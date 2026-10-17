# ruff: noqa: E501
"""CB9-K (flow-skewed touch maker, CH92) and CB9-D (dust-anchored midpoint, CH80 route 1): docs/research_lab/CREATIVE_BATCH_9.md sections 1.1-1.4,
2.1-2.8, CB9-K, CB9-D, CB9-F, 4 (q0185-q0187, the K/D block of q0189, q0192, q0197) and 5 (incl. the round-1 additions).

Data side: ``kd_frame`` (q0185: Gamma frame, key drops, <= 3 per event, seeded 1,000 markets, seeded event split SCREEN / HOLDOUT written before any
pmxt or print read), ``kd_books`` (q0186: pmxt hour 14Z of every window day, the 13Z lookback only for tokens without a ``book`` event by the origin;
origin states, per-minute D states, the hour's ``last_trade_price`` events; Data API prints ``[t - 6 h, t + 7 h]`` with hashed wallets; HOLDOUT
written under ``holdout/``) and ``kd_seal`` (q0187: seal-time drops, HOLDOUT listing sha256, seal copy ``seals/cb9_kd_holdout_SEAL.json``).
Analysis side: ``kd_census`` (counts only: cut points from feature values, gates GK / GD counted on the units that enter K1 / D1, the pmxt
coverage audit and labels, MDEs from declared assumptions), ``screen_kd`` (K1, D1 Stage 1 on SCREEN events) and ``rep_kd`` (K1-rep, D1-rep on
the sealed HOLDOUT events, only for advanced tests).

Exploratory historical data (pmxt v2 2026-04-13..08-10); no edge, calibration or profitability claim. AREPO never trades: every P&L here is a
paper rule at recorded prices. pmxt files are read one row group at a time with column projection and never materialised. A pmxt event is used
at ``t`` iff both clocks are <= ``t``; crossed books are reported, never repaired. Prints at or after the origin go to ``*_guarded`` files: only
``screen_kd`` / ``rep_kd`` open them in full; the census reaches them only through :class:`CountOnlyPosts` (yes / no and counts).
"""

from __future__ import annotations

import json
import math
import time
from bisect import bisect_right
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

import numpy as np

from . import cb3_maker as mk
from . import cb4_data as c4
from . import cb6_tail as c6
from . import cb7_common as c7
from . import cb8_books as bk
from . import cb8_common as cm
from . import cb8_flow as fl
from . import cb9_common as c9
from . import h5_seal
from . import history_backfill as hb
from . import history_sources as hs

# ---- declared constants (CREATIVE_BATCH_9.md; hashed into seals/cb9_kd_rules.json through declared() and rule_funcs()) -------------------------

RULES_VERSION = c9.RULES_VERSION_KD
FRAME_RUN, BOOKS_RUN = "kd_frame", "kd"
FRAME_COMPLETE, BOOKS_COMPLETE, INGRESS_CAP_STATUS = "kd_frame_complete", "kd_books_complete", "ingress_cap_reached"
SEAL_STATUS = "kd_sealed"
UNVERIFIED = c9.UNVERIFIED
SCREEN, HOLDOUT = "screen", "holdout"

WINDOW_START, WINDOW_END = "2026-04-13", "2026-08-10"  # K/D days d in [start, end) ...
PMXT_GAP = ("2026-06-12", "2026-06-18")  # ... minus the pmxt gap [06-12, 06-18)
MIN_OVERLAP_DAYS = 3.0
FRAME_END_FROM = "2026-04-16T00:00:00Z"  # a 3-day overlap needs end >= window start + 3 d
FRAME_END_BEFORE = "2026-10-01T00:00:00Z"  # T9_hist_end (design silent on the frame's end-date bound: conservative, closed markets only)
MIN_VOLUME = 10000.0
MAX_PER_EVENT = 3
N_SAMPLE = 1000
SPORTS_MAX_SHARE = 0.15
SEED_SAMPLE = "arepo-cb9-kd-sample"
SEED_SPLIT = "arepo-cb9-kd-split"
SEED_ORDER = "arepo-cb9-kd-order"
PYTH_HOST = "pythdata.app"

ORIGIN_HOUR, LOOKBACK_HOUR = 14, 13
FRESH_S = 3600
TOP_LEVELS = 10
N_MINUTES = 60
PRINT_PRE_S = 6 * 3600
PRINT_POST_S = 7 * 3600
PRINT_PAGES = 10
PRINT_LIMIT = 1000
INGRESS_CAP_GB = 90.0
FRAME_OUTPUT_CAP_GB = 0.01
BOOKS_OUTPUT_CAP_GB = 0.15
DATA_DUMPS_CAP_GB = c9.DATA_DUMPS_CAP_GB
MAX_RPS_FRAME, MAX_RPS_BOOKS, MAX_RPS_SEAL = 2.0, 4.0, 2.0

# K
X6_CLIP, X6_SD = 1.0, 0.8578247852488129  # HB2 frozen x6 scaling (battery2.X6_CLIP / X6_SD; a unit test pins equality)
X6_WINDOW_S = 6 * 3600
RV_WINDOW_S = 6 * 3600  # OPEN ITEM: the design says "1-day RV"; the declared print fetch covers [t - 6 h, t) only (see declared()["open_items"])
RV_GRID_S = 600
RV_EPS = 1e-4
RV_MIN_DIFFS = 3
CELL_QUANTILE = 2.0 / 3.0
SKEW_QUANTILE = 0.5
QUOTE_LIFE_S = 7200
QUOTE_SHARES = 50.0
POSTED_SHARES = 2 * QUOTE_SHARES
SKEW_TICKS = 1
MARK_FROM_S, MARK_TO_S = 5 * 3600, 7 * 3600
LATENCY_S = 60
DEFAULT_TICK = 0.01
K1_FLOOR_C = 0.5
KILL2_FLOOR_C = 0.5
GK = {"cell_origins": 2000, "filled_origins_per_type": 300, "events": 60, "days": 30}
K_MONTH_MIN_FILLS = 300

# D
NEXT_TX_FROM_S, NEXT_TX_TO_S = 1, 600
EPISODE_STEP_MIN = 5
USD_VARIANT_MIN = 1.0
D1_FLOOR_C = 0.5
GD = {"dust_share": 0.05, "units": 1000, "market_days": 100}
D_MONTH_MIN_UNITS = 500

# audit, labels, MDE assumptions (reported only; never used to change a floor)
AUDIT_PASS = 0.90
AVAILABLE_MIN = 0.80
MDE_Z = 2.326 + 0.842  # one-sided alpha 0.01, power 0.80
K_MARKOUT_SD_C, K_DEFF = 4.0, 1.5
D_SD_C, D_DEFF = 1.5, 2.0

LABEL_SOURCE_UNAVAILABLE, LABEL_NO_FRESH_BOOK, LABEL_AVAILABLE, LABEL_NOT_PROCESSED = "source unavailable", "no fresh book", "available", "not processed"

FRAME_COLUMNS = ["market_id", "condition_id", "token0", "token1", "event_id", "event_ids", "neg_risk_market_id", "series_ids", "fee_category", "topic",
                 "start_at", "end_at", "start_epoch", "end_epoch", "volume", "liquidity", "order_min_size", "tick_size", "neg_risk", "neg_risk_augmented",
                 "resolution_host", "question", "event_title"]
SAMPLE_COLUMNS = [*FRAME_COLUMNS, "group", "stratum", "stratum_size", "stratum_alloc", "sample_weight", "split", "event_key", "n_days", "days"]
PRINT_COLUMNS = ["market_id", "day", "ts", "idx", "asset", "side", "price", "size", "yes_price", "yes_side", "wallet_hash", "tx", "api_rank"]
LTP_COLUMNS = ["market_id", "day", "idx", "asset", "v_ms", "r_ms", "price", "size", "side", "tx"]
ORIGIN_COLUMNS = ["market_id", "day", "idx", "t_ms", "has_book", "fresh", "crossed", "best_bid", "bid_size", "best_ask", "ask_size", "bids_top", "asks_top",
                  "tick", "tick_source", "fee_bps", "last_event_ms", "n_events", "book_status", "lookback", "min_size"]
MINUTE_COLUMNS = ["market_id", "day", "idx", "minute", "u_ms", "has_book", "fresh", "crossed", "best_bid", "bid_size", "best_ask", "ask_size", "cut_bid", "cut_ask",
                  "cut_bid_usd", "cut_ask_usd", "last_event_ms", "book_status"]
MARKET_DAY_COLUMNS = ["market_id", "day", "split", "event_key", "books_status", "lookback", "n_events_span", "n_events_tok0", "n_events_tok1", "prints_status",
                      "n_prints_pre", "n_prints_post", "n_prints_span", "pages"]
DAY_COLUMNS = ["day", "n_screen", "n_holdout", "books_status", "prints_status", "lookback_status", "bytes_read"]
EVENT_COLS_KD = [*bk.EVENT_COLS, "transaction_hash"]

# file layout (A's q0188 sign audit B reads the SCREEN print files through these constants)
ORIGINS_SUFFIX = ".origins.csv.gz"
MINUTES_SUFFIX = ".minutes.csv.gz"
LTP_SUFFIX = ".ltp.csv.gz"
PRINTS_PRE_SUFFIX = ".prints_pre.csv.gz"  # prints with ts < t (features)
PRINTS_POST_SUFFIX = ".prints_post_guarded.csv.gz"  # prints with ts >= t (fills, marks, next transactions): guarded
MARKETS_FILE = "markets.csv.gz"
SAMPLE_FILE, SPLIT_FILE, FRAME_FILE = "sample.csv.gz", "split.json", "frame.csv.gz"
SEAL_NAME = "holdout_SEAL.json"
SEAL_COPY_NAME = "cb9_kd_holdout_SEAL.json"
DROPS_FILE = "drops.csv.gz"
ACCESS_LOG = "ACCESS_LOG.jsonl"
RESULTS_NAME, REP_RESULTS_NAME = "results_KD.json", "results_KD_rep.json"
FRAME_DIR = c9.CB9_DIR / FRAME_RUN
BOOKS_DIR = c9.CB9_DIR / BOOKS_RUN
SCREEN_PRINT_DIR = BOOKS_DIR / SCREEN
SCREEN_PRINT_GLOBS = ("*" + PRINTS_PRE_SUFFIX, "*" + PRINTS_POST_SUFFIX)
SCREEN_LTP_GLOB = "*" + LTP_SUFFIX
SCREEN_PRINT_FORMAT = {"columns": PRINT_COLUMNS, "ts": "venue timestamp (s)", "side": "+1 BUY / -1 SELL (Data API, token terms)", "idx": "outcomeIndex",
                       "asset": "token id of idx (from the frame)", "wallet_hash": "HMAC-SHA256(key, lower-cased proxyWallet), first 32 hex (cb8_common.hash_wallet)",
                       "tx": "full transactionHash", "api_rank": "position in the Data API reply order within the market-day window (0 = newest)",
                       "ltp_columns": LTP_COLUMNS}


def declared() -> dict:
    return {
        "frame": {"query": f"Gamma /markets closed=true, volume_num_min={MIN_VOLUME:g}, end_date per UTC day in [{FRAME_END_FROM}, {FRAME_END_BEFORE}), order id; halved while capped (one day minimum: excluded, counted)",
                  "keeps": f"binary with token ids; scheduled life [startDate, endDate) overlapping [{WINDOW_START}, {WINDOW_END}) by >= {MIN_OVERLAP_DAYS:g} d; volume >= {MIN_VOLUME:g} (end-of-life field, disclosed look-ahead in selection); "
                           f"not negRiskAugmented; not weather (fee_category or CB2-W text); not crypto Up/Down (CB1_UPDOWN_RE); not Pyth (resolutionSource host *{PYTH_HOST})",
                  "stored_fields": FRAME_COLUMNS, "outcome_fields_stored": False},
        "exclusion": {"keys": "creative_batch9/exclusion_keys.csv.gz + exclusion_report.json (q0182); report disjointness_unverified -> K1, D1 not testable (counted)",
                      "order": "filters -> id / key drops -> <= 3 per event -> seeded sample -> event split"},
        "sample": {"seed": SEED_SAMPLE, "n": N_SAMPLE, "max_per_event": MAX_PER_EVENT, "cap_order": f"sha256({SEED_SAMPLE}|cap|market_id)",
                   "sports": f"topic == 'sports' sampled into its own reported stratum, n_sports = min(pool, floor({SPORTS_MAX_SHARE} n), round(n * pool share))",
                   "strata": "group x fee_category, proportional (cb8_flow.flow_sample)"},
        "split": {"seed": SEED_SPLIT, "unit": "Gamma event (first event id; market id if none)", "rule": "int(sha256(seed|event), 16) % 2: 0 SCREEN, 1 HOLDOUT",
                  "written_before_first_pmxt_or_print_read": True},
        "days": {"window": [WINDOW_START, WINDOW_END], "pmxt_gap": list(PMXT_GAP), "origin": f"t = d {ORIGIN_HOUR:02d}:00Z",
                 "market_day": "start_epoch <= t and end_epoch >= t + 7 h (scheduled life)", "order_seed": SEED_ORDER, "order": "days by sha256(seed|day); an ingress cap truncates evenly"},
        "pmxt": {"hour": ORIGIN_HOUR, "lookback_hour": LOOKBACK_HOUR, "lookback": "per token, only when the token has no `book` event with both clocks <= t in hour 14Z",
                 "clock_rule": "an event is used at x iff timestamp <= x and timestamp_received <= x", "fresh_s": FRESH_S, "top_levels": TOP_LEVELS,
                 "reader": "row groups pruned on market statistics, light columns first, heavy columns only for row groups with a matching row; never materialised",
                 "columns": EVENT_COLS_KD, "ingress_cap_gb": INGRESS_CAP_GB, "kept": "origin states (both tokens), per-minute D states (both tokens), last_trade_price events of the hour (with transaction_hash)"},
        "prints": {"window": f"[t - {PRINT_PRE_S // 3600} h, t + {PRINT_POST_S // 3600} h] venue time, takerOnly", "pages": PRINT_PAGES, "limit": PRINT_LIMIT,
                   "capped": "unavailable (counted)", "pre": "ts < t (features)", "post": "ts >= t (guarded)", "wallet": "HMAC hash only (strict loader, pinned fingerprint)"},
        "k": {"state": "outcome-0 token at t; fresh = latest event >= t - 3600 s; crossed or one-sided ineligible",
              "x6": f"HB2 f_imb_6h on prints in [t - 6 h, t): sum(yes_side * size * price) / sum(size * price); clip [-{X6_CLIP:g}, {X6_CLIP:g}] / {X6_SD}",
              "rv": f"log(rms of consecutive {RV_GRID_S} s grid differences of the last-print YES price over [t - {RV_WINDOW_S} s, t) + {RV_EPS}); >= {RV_MIN_DIFFS} differences",
              "spr": "best ask - best bid of the outcome-0 token at t",
              "cell": f"RV >= SCREEN quantile {CELL_QUANTILE:.6f} of RV or SPR >= SCREEN quantile {CELL_QUANTILE:.6f} of SPR (numpy linear; feature values of eligible SCREEN origins only; frozen in the census)",
              "skew_cut": f"|x6| >= SCREEN quantile {SKEW_QUANTILE} of |x6| over eligible SCREEN cell origins; else no skew (excluded from K1, counted)",
              "quotes": f"life [t, t + {QUOTE_LIFE_S} s], {QUOTE_SHARES:g} shares each side; unskewed = touch; s = +1: bid + {SKEW_TICKS} tick if < best ask else bid, ask + {SKEW_TICKS} tick (if <= 1 - tick); s = -1 mirrored",
              "tick": "latest pmxt tick_size_change with both clocks <= t, else Gamma orderPriceMinTickSize, else 0.01",
              "fills": "cb3_maker.quote_fills queue rule, depth = displayed size at the quote price (0 inside the spread), own = 50; YES-terms prints (complementary prints converted)",
              "fills_through": "binding bracket: cumulative strictly-through opposite volume in (t, t + life) >= 50",
              "mark": f"mid of the last taker-BUY and last taker-SELL YES prices in [t + {MARK_FROM_S} s, t + {MARK_TO_S} s]; both required, else the origin's fills are unavailable",
              "statistic": "per origin, mean mark-out per filled share by quote type; K1 = mean over origins with a skewed fill - mean over origins with an unskewed fill (cents); unit value = delta-method linearisation (origins equally weighted)",
              "floor_c": K1_FLOOR_C, "route_gate": "skewed mean per filled share > 0 AND skewed mean net per origin (P&L / 100 posted shares, unfilled = 0) > 0",
              "kill2": f"unskewed alone >= {KILL2_FLOOR_C}c with p < 0.01 -> 'CB3-B's maker result; skew not needed' (no advance)",
              "gate_gk": GK, "gk_counted_on": "the units that enter K1 (cell, after the skew cut, prints available, mark available)",
              "clusters": ["event", "day"], "placebo_seed": c9.PLACEBO_SEEDS["K1_skew_sign"], "rebate": "reported only: economics.REBATE_SHARE x recorded fee rate x p(1 - p)",
              "robustness": {"cost": "trade-through fills keep the sign and >= half", "top5": "p and floor without the top 5 clusters of each way",
                             "weighting": "pooled per filled share agrees in sign", "months": f"sign in >= 2/3 of months with >= {K_MONTH_MIN_FILLS} fills (none: unknown, not met)",
                             "worst_case": "unavailable marks scored at -1 tick per filled share keep the sign and p", "latency": f"fills only from t + {LATENCY_S} s keep the sign and >= half"}},
        "d": {"unit": f"market-minute u in [14:01Z, 15:00Z] on the outcome-0 token's book (two-sided, fresh, not crossed); at most one unit per dust episode per {EPISODE_STEP_MIN} minutes (the first)",
              "dust": "best bid or best ask size < the market's recorded orderMinSize (missing field: unavailable, counted)",
              "dust_variant": f"share-or-${USD_VARIANT_MIN:g}: size < orderMinSize or size x price < {USD_VARIANT_MIN:g} (reported only)",
              "m_d": "(best bid + best ask) / 2", "m_c": "mid of the best bid and best ask among levels with size >= orderMinSize (unavailable if either side has none)",
              "next_tx": f"first transaction hash among outcome-0 prints with ts in [u + {NEXT_TX_FROM_S} s, u + {NEXT_TX_TO_S} s] (ties: earliest ts, then oldest in API order)",
              "P": "size-weighted VWAP of all of that transaction's prints on the token; last fill (newest in API order) reported; side never used",
              "statistic": "mean |P - m_d| - |P - m_c| in cents", "floor_c": D1_FLOOR_C, "gate_gd": GD,
              "gd_counted_on": "two-sided fresh market-minutes; units entering D1 (m_c available, next transaction found)", "clusters": ["market_day", "day"],
              "placebo_seed": c9.PLACEBO_SEEDS["D1_shuffle"], "robustness": {"top5": True, "weighting": "next-transaction size", "months": f">= {D_MONTH_MIN_UNITS} units"}},
        "audit": {"rule": "(market, day) with >= 1 Data API print in [14:00Z, 15:00Z): pmxt shows any event of the condition id in the span", "pass": AUDIT_PASS,
                  "labels": [LABEL_SOURCE_UNAVAILABLE, LABEL_NO_FRESH_BOOK, "no opportunity (gate fail with audit pass and >= 80% of SCREEN units source-available)"],
                  "available_min": AVAILABLE_MIN},
        "mde_assumptions": {"z": MDE_Z, "k_markout_sd_c": K_MARKOUT_SD_C, "k_deff": K_DEFF, "d_sd_c": D_SD_C, "d_deff": D_DEFF, "use": "reported only; never changes a floor"},
        "seal": {"copy": SEAL_COPY_NAME, "drops": "seal-time drops by id and key against every committed seal copy except CB9's own; sealed files never edited",
                 "read_rule": "holdout/ is opened only by rep-kd after K1 or D1 advanced and its Stage-1 result is recorded (trials line with the results sha256)"},
        "outputs": {"frame": f"{FRAME_RUN}/{{{FRAME_FILE},{SAMPLE_FILE},{SPLIT_FILE},manifest.json}}", "books": f"{BOOKS_RUN}/{{screen,holdout}}/<day>{{{ORIGINS_SUFFIX},{MINUTES_SUFFIX},{LTP_SUFFIX},{PRINTS_PRE_SUFFIX},{PRINTS_POST_SUFFIX}}} + <split>/{MARKETS_FILE}",
                    "caps_gb": {"frame": FRAME_OUTPUT_CAP_GB, "books": BOOKS_OUTPUT_CAP_GB}, "data_dumps_cap_gb_default": DATA_DUMPS_CAP_GB},
        "open_items": [
            "RV: the design says the 1-day realised volatility of print prices, but the declared print fetch is [t - 6 h, t + 7 h]; RV is computed on [t - 6 h, t) (RV_WINDOW_S) until the freeze check decides (widen the fetch to t - 24 h, or keep the 6 h analogue)",
            "Origin t = 14:00:00Z is the first instant of hour 14Z, so nearly every token needs the 13Z lookback (about 2x ingress per day; the 90 GB cap may truncate days, counted)",
            "D uses the outcome-0 token's book and prints (one unit per market-minute); both tokens' minute states are stored",
            "Book events are kept as derived per-minute D states plus raw last_trade_price events (raw book JSON is not stored: 0.15 GB output cap)",
        ],
    }


# ---- days, frame ------------------------------------------------------------------------------------------------------------------------


def window_days() -> list[str]:
    d0, d1 = date.fromisoformat(WINDOW_START), date.fromisoformat(WINDOW_END)
    g0, g1 = date.fromisoformat(PMXT_GAP[0]), date.fromisoformat(PMXT_GAP[1])
    out = []
    for i in range((d1 - d0).days):
        d = d0 + timedelta(days=i)
        if not (g0 <= d < g1):
            out.append(d.isoformat())
    return out


def origin_epoch(day: str) -> float:
    return datetime(*date.fromisoformat(day).timetuple()[:3], ORIGIN_HOUR, tzinfo=UTC).timestamp()


def _num(x) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return math.nan
    return v


def kd_row(m: dict) -> dict | None:
    """Slim frame row of one Gamma market (no outcome price, no closing field). ``None`` unless binary with token ids."""
    r = hb.frame_row(m, with_text=True)
    if r is None:
        return None
    k = c6.key_fields(m)
    src = str(m.get("resolutionSource") or "")
    try:
        host = (urlparse(src).hostname or "").lower() if src else ""
    except ValueError:
        host = ""
    out = {c: r.get(c, "") for c in FRAME_COLUMNS if c in r}
    out.update(event_ids=k["event_ids"], neg_risk_market_id=k["neg_risk_market_id"], series_ids=k["series_ids"], order_min_size=_num(m.get("orderMinSize")),
               tick_size=_num(m.get("orderPriceMinTickSize")), neg_risk_augmented=int(bool(m.get("negRiskAugmented"))), resolution_host=host)
    return {c: out.get(c, "") for c in FRAME_COLUMNS}


def overlap_days(r: dict) -> float:
    se, ee = _num(r.get("start_epoch")), _num(r.get("end_epoch"))
    if not (math.isfinite(se) and math.isfinite(ee)):
        return math.nan
    w0 = datetime.fromisoformat(WINDOW_START).replace(tzinfo=UTC).timestamp()
    w1 = datetime.fromisoformat(WINDOW_END).replace(tzinfo=UTC).timestamp()
    return max(0.0, min(ee, w1) - max(se, w0)) / cm.DAY


def frame_reason(r: dict) -> str | None:
    """Why a frame row leaves the frame (``None`` = kept). Listing and text fields only."""
    ov = overlap_days(r)
    if not math.isfinite(ov):
        return "no_dates"
    if ov < MIN_OVERLAP_DAYS:
        return "overlap_below_min"
    vol = _num(r.get("volume"))
    if not (math.isfinite(vol) and vol >= MIN_VOLUME):
        return "volume_below_min"
    if str(r.get("neg_risk_augmented")) in ("1", "True", "true"):
        return "neg_risk_augmented"
    if c7.is_weather(str(r.get("fee_category") or ""), str(r.get("question") or ""), str(r.get("event_title") or "")):
        return "weather"
    if hb.CB1_UPDOWN_RE.search(f"{r.get('question', '')} {r.get('event_title', '')}"):
        return "crypto_updown"
    host = str(r.get("resolution_host") or "")
    if host == PYTH_HOST or host.endswith("." + PYTH_HOST):
        return "pyth"
    return None


def market_days(r: dict) -> list[str]:
    """Window days whose origin ``t`` lies in the scheduled life with the mark window inside it: start <= t and end >= t + 7 h."""
    se, ee = _num(r.get("start_epoch")), _num(r.get("end_epoch"))
    if not (math.isfinite(se) and math.isfinite(ee)):
        return []
    return [d for d in window_days() if se <= origin_epoch(d) and ee >= origin_epoch(d) + MARK_TO_S]


def frame_walk_days() -> list[str]:
    d0 = datetime.fromtimestamp(cm.ep(FRAME_END_FROM), UTC).date()
    d1 = datetime.fromtimestamp(cm.ep(FRAME_END_BEFORE) - 1, UTC).date()
    return [(d0 + timedelta(days=i)).isoformat() for i in range((d1 - d0).days + 1)]


def _walk_window(lim: hb.Limiter, a: int, b: int, acc: dict) -> None:
    f = "%Y-%m-%dT%H:%M:%SZ"
    p = {"closed": "true", "volume_num_min": int(MIN_VOLUME), "order": "id", "ascending": "true",
         "end_date_min": datetime.fromtimestamp(a, UTC).strftime(f), "end_date_max": datetime.fromtimestamp(b, UTC).strftime(f)}
    batch, capped, failed = c4._paged_strict(lim, p, hb.GAMMA_OFFSET_CAP)
    if failed:
        acc["failed_windows"] += 1
        return
    if capped and b - a > 3600:
        acc["splits"] += 1
        mid = a + (b - a) // 2
        _walk_window(lim, a, mid, acc)
        _walk_window(lim, mid, b, acc)
        return
    acc["windows"] += 1
    if capped:
        acc["excluded_capped_window"] += 1
        return
    acc["batches"].extend(batch)


def walk_frame(fr: cm.Cb8Run, days: list[str], should_stop: Callable[[], bool] | None = None) -> str | None:
    """One gzip member per UTC end-date day in ``frame_partial.jsonl.gz`` (rows already reduced to the frame fields). A day with a failed request is
    retried by a later chunk (at most 3 attempts; then counted as failed). Returns a stop reason or ``None`` when every day is done."""
    pp, pf = fr.rdir / "frame_partial.jsonl.gz", fr.rdir / "frame_fail.jsonl"
    done = {rec["day"] for rec in c6.iter_partial(pp)}
    fails = c7.walk_failed_days(pf)
    for d in days:
        if d in done or fails.get(d, 0) >= cm.MAX_ITEM_ATTEMPTS:
            continue
        why = fr.stop_reason(should_stop)
        if why:
            return why
        a = int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=UTC).timestamp())
        acc = {"batches": [], "splits": 0, "windows": 0, "failed_windows": 0, "excluded_capped_window": 0}
        _walk_window(fr.lim, a, a + int(cm.DAY), acc)
        if acc["failed_windows"]:
            with pf.open("a") as fh:
                fh.write(json.dumps({"day": d}) + "\n")
            fr.counts["frame_request_failures"] = fr.counts.get("frame_request_failures", 0) + 1
            continue
        raw = [m for m in acc["batches"] if isinstance(m, dict)]
        rows = [x for x in (kd_row(m) for m in raw) if x is not None]
        c7.append_member(fr, pp, {"day": d, "rows": rows, "n_raw": len(raw), "n_not_binary": len(raw) - len(rows), "splits": acc["splits"],
                                  "excluded_capped_window": acc["excluded_capped_window"]})
    fails = c7.walk_failed_days(pf)
    have = {r["day"] for r in c6.iter_partial(pp)}
    return None if all(d in have or fails.get(d, 0) >= cm.MAX_ITEM_ATTEMPTS for d in days) else "frame_paused"


def kd_sample(rows: list[dict], n: int = N_SAMPLE, seed: str = SEED_SAMPLE) -> tuple[list[dict], dict]:
    """``n`` markets: sports into its own stratum (at most 15%, otherwise proportional to the pool), the rest ``group x fee_category`` proportional;
    order by sha256(seed|market_id). Reads ids and listing categories only."""
    pool_sports = sum(1 for r in rows if r.get("topic") == "sports")
    pool_main = len(rows) - pool_sports
    n_eff = min(n, len(rows))
    n_sports = min(pool_sports, int(math.floor(SPORTS_MAX_SHARE * n)), int(round(n_eff * pool_sports / len(rows)))) if rows else 0
    n_main = min(n_eff - n_sports, pool_main)
    sample, rep = fl.flow_sample(rows, n_main, n_sports, seed)
    rep.update(n_requested=n, n_main=n_main, n_sports=n_sports, pool_main=pool_main, pool_sports=pool_sports)
    return sample, rep


def assemble_kd(frame: list[dict], excl_ids: set[str], excl_keys: dict[str, set[str]], n: int = N_SAMPLE) -> tuple[list[dict], dict]:
    """Stage order: filters, id / key drops, per-event cap (<= 3), seeded sample, event split, market-days. The split is final before any pmxt
    or print read."""
    rep: dict = {"n_frame_in": len(frame), "filtered": {}}
    kept = []
    for r in frame:
        why = frame_reason(r)
        if why:
            rep["filtered"][why] = rep["filtered"].get(why, 0) + 1
        else:
            kept.append(r)
    rep["n_after_filters"] = len(kept)
    after, drops = c9.drop_by_keys(kept, excl_ids, excl_keys)
    rep["drops"] = drops
    rep["n_after_drops"] = len(after)
    capped, n_cap = fl.per_event_cap(after, SEED_SAMPLE, MAX_PER_EVENT)
    rep["capped_out_per_event"] = n_cap
    sample, srep = kd_sample(capped, n)
    rep["sample"] = srep
    out = []
    no_days = 0
    for r in sample:
        days = market_days(r)
        if not days:
            no_days += 1
        out.append({**r, "split": fl.event_split(r, SEED_SPLIT), "event_key": fl.event_key(r), "n_days": len(days), "days": ";".join(days)})
    out.sort(key=lambda x: x["market_id"])
    rep["n_sample"] = len(out)
    rep["n_without_market_days"] = no_days
    rep["n_screen"] = sum(1 for r in out if r["split"] == SCREEN)
    rep["n_holdout"] = len(out) - rep["n_screen"]
    rep["n_market_days"] = {s: sum(int(r["n_days"]) for r in out if r["split"] == s) for s in (SCREEN, HOLDOUT)}
    return out, rep


def read_sample(frame_dir: Path) -> list[dict]:
    rows = []
    for r in c7.read_csv_gz(Path(frame_dir) / SAMPLE_FILE):
        r["days"] = [d for d in str(r.get("days") or "").split(";") if d]
        for k in ("start_epoch", "end_epoch", "volume", "liquidity", "order_min_size", "tick_size"):
            r[k] = _num(r.get(k))
        rows.append(r)
    return rows


def _manifest_done(rdir: Path, statuses: tuple[str, ...]) -> dict | None:
    mp = Path(rdir) / "manifest.json"
    prior = json.loads(mp.read_text()) if mp.exists() else {}
    if prior.get("complete") is True and prior.get("stopped") is None and prior.get("status") in statuses:
        return prior
    return None


def kd_frame(root: Path, transport, *, rules_sha: str, exclusion_keys_path: Path | None = None, n: int = N_SAMPLE, rps: float = MAX_RPS_FRAME,
             disk_cap: int = int(FRAME_OUTPUT_CAP_GB * 1024**3), budget_min: float | None = None, data_dumps: Path | None = None,
             data_dumps_cap_gb: float = DATA_DUMPS_CAP_GB, wall_clock: Callable[[], float] = time.time, sleep=time.sleep, live_check=None, health_check=None,
             snapshot_root: Path | None = None, should_stop: Callable[[], bool] | None = None, now: float | None = None, run_id: str = FRAME_RUN,
             t_seal_epoch: float = c9.T_SEAL_EPOCH) -> dict:
    """q0185, one resumable chunk. Refusals (run id, root, T_seal, exclusion files) -> sticky end states -> headroom (exit 75) -> the frame walk
    -> disjointness check -> sample and split (``split.json`` and ``sample.csv.gz``; written before any pmxt or print read)."""
    root = Path(root)
    c9.refuse_run_id(run_id, FRAME_RUN)
    c9.refuse_path(root)
    c9.require_after_t_seal(time.time() if now is None else now, "kd-frame", t_seal_epoch)
    ids, ksets, krep, ksha = c9.load_exclusion_keys(Path(exclusion_keys_path or c9.EXCLUSION_KEYS_DEFAULT))
    rdir = root / run_id
    done = _manifest_done(rdir, (FRAME_COMPLETE,))
    if done:
        return {"stopped": None, "status": FRAME_COMPLETE, "complete": True, "counts": done.get("counts")}
    if (rdir / "DISJOINTNESS_UNVERIFIED.json").exists():
        return {"stopped": UNVERIFIED, "status": UNVERIFIED, "complete": True}
    term = cm.prior_terminal(rdir)
    if term:
        return term
    cm.require_room(data_dumps, data_dumps_cap_gb, disk_cap)
    fr = cm.open_run(root, run_id, transport, allowed_run_id=FRAME_RUN, kind="cb9_kd_frame", label="CB9-K/D frame",
                     params={"n": n, "evidence_role": c9.EVIDENCE_ROLE_HIST, "exclusion_keys_sha256": ksha}, rules_sha=rules_sha, key_fp="", disk_cap=disk_cap,
                     rps=min(rps, MAX_RPS_FRAME), budget_min=budget_min, now=now, sleep=sleep, live_check=live_check, wall_clock=wall_clock,
                     snapshot_root=snapshot_root, health_check=health_check)
    fr.extra_state["exclusion_keys_sha256"] = ksha
    why = fr.unhealthy()
    if why:
        m = fr.manifest(why, {"transient": True})
        m["status"] = "in_progress"
        return m
    try:
        stopped = walk_frame(fr, frame_walk_days(), should_stop)
        if stopped:
            m = fr.manifest(stopped, {"transient": True})
            m["status"] = "in_progress"
            return m
        if krep.get("disjointness") == UNVERIFIED:
            (rdir / "DISJOINTNESS_UNVERIFIED.json").write_text(json.dumps({"run_id": run_id, "exclusion_report_disjointness": UNVERIFIED,
                                                                            "rule": "design 1.3: > 2% of exclusion ids without metadata -> K1, D1 not testable (p = 1, counted)"}, indent=1, sort_keys=True))
            m = fr.manifest(None, {"complete": True, "status": UNVERIFIED})
            m["status"] = UNVERIFIED
            return m
        recs = list(c6.iter_partial(rdir / "frame_partial.jsonl.gz"))
        frame = [r for rec in recs for r in rec["rows"]]
        failed_days = sorted(d for d, k in c7.walk_failed_days(rdir / "frame_fail.jsonl").items() if k >= cm.MAX_ITEM_ATTEMPTS)
        sample, rep = assemble_kd(frame, ids, ksets, n)
        rep["frame_walk"] = {"days": len(frame_walk_days()), "frame_rows": len(frame), "n_raw": sum(r.get("n_raw", 0) for r in recs),
                             "n_not_binary": sum(r.get("n_not_binary", 0) for r in recs), "excluded_capped_window": sum(r.get("excluded_capped_window", 0) for r in recs),
                             "failed_days": failed_days}
        fr.budget.write_gz_csv(rdir / FRAME_FILE, FRAME_COLUMNS, ([r.get(c, "") for c in FRAME_COLUMNS] for r in frame))
        fr.budget.write(rdir / SPLIT_FILE, json.dumps({"seeds": {"sample": SEED_SAMPLE, "split": SEED_SPLIT, "order": SEED_ORDER}, "report": rep,
                                                       "events": {r["event_key"]: r["split"] for r in sample}}, indent=1, sort_keys=True, default=float).encode())
        fr.budget.write_gz_csv(rdir / SAMPLE_FILE, SAMPLE_COLUMNS, ([r.get(c, "") for c in SAMPLE_COLUMNS] for r in sample))
        for name in (FRAME_FILE, SPLIT_FILE, SAMPLE_FILE):
            fr.record_file(rdir / name)
        (rdir / "frame_partial.jsonl.gz").unlink(missing_ok=True)
        (rdir / "frame_fail.jsonl").unlink(missing_ok=True)
        fr.counts.update(n_sample=rep["n_sample"], n_screen=rep["n_screen"], n_holdout=rep["n_holdout"])
    except OSError as exc:
        return cm.disk_budget_end(fr, exc)
    m = fr.manifest(None, {"complete": True, "status": FRAME_COMPLETE})
    m["status"] = FRAME_COMPLETE
    return m


# ---- pmxt: streaming reader and states ------------------------------------------------------------------------------------------------------


def read_events_kd(hour: datetime, tokens: dict[str, str], *, fetch, size_fn, cut_ms: int, gate: Callable[[], None] | None = None,
                   meter: Callable[[int], None] | None = None) -> tuple[dict[str, list[dict]], dict]:
    """``cb8_books.read_hour_events`` with ``transaction_hash`` kept (``tx``): events of ``tokens`` (token -> condition id) in one pmxt hour file with
    both clocks <= ``cut_ms``, sorted by (venue, receipt) time. Row groups are pruned on the ``market`` statistics; the light columns are read first and
    the heavy ones only for row groups with a matching row (one row group at a time, never the whole hour). Raises ``cb8_books.HourMissing`` /
    ``HourCorrupt``; a network failure propagates. ``meter`` receives the bytes fetched even when the read fails."""
    import pyarrow as pa  # noqa: PLC0415
    import pyarrow.compute as pc  # noqa: PLC0415
    import pyarrow.parquet as pq  # noqa: PLC0415

    url = hs.pmxt_url(hour)
    try:
        size = size_fn(url)
    except FileNotFoundError:
        raise bk.HourMissing(url) from None
    rf = hs.RangeFile(url, size, fetch)
    ev: dict[str, list[dict]] = {t: [] for t in tokens}
    info = {"bytes": 0, "row_groups_total": 0, "row_groups_read": 0, "rows": 0}
    try:
        pf = pq.ParquetFile(rf)
        names = set(pf.schema_arrow.names)
        cols = [c for c in EVENT_COLS_KD if c in names]
        midx = pf.schema_arrow.get_field_index("market")
        want = {c.lower() for c in tokens.values()}
        info["row_groups_total"] = pf.num_row_groups
        value_set = pa.array(sorted(tokens), type=pa.string())
        for rg in range(pf.num_row_groups):
            ms = pf.metadata.row_group(rg).column(midx).statistics
            if ms is not None and ms.has_min_max and not any(hs._b(ms.min) <= c <= hs._b(ms.max) for c in want):
                continue
            if gate is not None:
                gate()
            light = pf.read_row_group(rg, columns=["timestamp_received", "timestamp", "asset_id"])
            mine = pc.is_in(light["asset_id"], value_set=value_set)
            r_ms, v_ms = bk._ms(light["timestamp_received"]), bk._ms(light["timestamp"])
            bk._check_clock(url, hour, r_ms.filter(mine), v_ms.filter(mine))
            keep = pc.and_(mine, pc.and_(pc.less_equal(r_ms, cut_ms), pc.less_equal(v_ms, cut_ms)))
            if not pc.any(keep).as_py():
                continue
            info["row_groups_read"] += 1
            tbl = pf.read_row_group(rg, columns=cols).filter(keep)
            data = {c: tbl[c].to_pylist() for c in cols if c not in ("timestamp_received", "timestamp")}
            rr, vv = bk._ms(tbl["timestamp_received"]).to_pylist(), bk._ms(tbl["timestamp"]).to_pylist()

            def col(name, i, data=data):
                return data[name][i] if name in data else None

            for i in range(tbl.num_rows):
                ev[data["asset_id"][i]].append({"et": data["event_type"][i], "v": vv[i], "r": rr[i], "bids": col("bids", i), "asks": col("asks", i),
                                                "price": col("price", i), "size": col("size", i), "side": col("side", i), "tick": col("new_tick_size", i),
                                                "fee": col("fee_rate_bps", i), "tx": col("transaction_hash", i)})
            info["rows"] += tbl.num_rows
    except (pa.ArrowException, KeyError, ValueError, TypeError, IndexError) as exc:
        raise bk.HourCorrupt(f"{url}: {type(exc).__name__}") from None
    finally:
        info["bytes"] = rf.bytes_fetched
        if meter is not None:
            meter(rf.bytes_fetched)
    for lst in ev.values():
        lst.sort(key=lambda e: (e["v"], e["r"]))
    return ev, info


def _fee(e: dict) -> float | None:
    f = e.get("fee")
    if f is None:
        return None
    try:
        v = float(f)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(v) else v


def kd_state(events: list[dict], t_ms: int, *, min_size: float = math.nan, vs: list[int] | None = None, ticks: list[tuple[int, int, str]] | None = None,
             count_events: bool = False) -> dict:
    """State of one token at ``t_ms`` from events sorted by (venue, receipt) time with BOTH clocks <= ``t_ms``: the last ``book`` event, then later
    ``price_change`` events (size = new absolute level total, 0 removes). Reports best bid / ask and their sizes, the top 10 levels of each side, the
    size-cutoff best levels (size >= ``min_size``; and the share-or-$1 variant), the tick of the latest ``tick_size_change``, the fee rate of the latest
    event with one, the venue time of the latest event of any type, ``fresh`` (that time >= t - 3600 s), ``crossed`` and ``book_status`` (``book`` /
    ``book_unavailable`` (events, no snapshot) / ``no_events``). Crossed books are reported, never repaired. ``vs`` (venue times) and ``ticks``
    (``(v, r, tick)`` of the tick_size_change events) may be passed precomputed."""
    if vs is None:
        vs = [e["v"] for e in events]
    if ticks is None:
        ticks = [(e["v"], e["r"], str(e["tick"])) for e in events if e["et"] == "tick_size_change" and e.get("tick") is not None]
    hi = bisect_right(vs, t_ms)
    last_v = book_i = fee = None
    i = hi - 1
    while i >= 0 and (book_i is None or fee is None):  # back to the last eligible snapshot (and the latest fee, usually on the same events)
        e = events[i]
        if e["r"] <= t_ms:
            if last_v is None:
                last_v = e["v"]
            if fee is None:
                fee = _fee(e)
            if book_i is None and e["et"] == "book":
                book_i = i
        i -= 1
    tick = next((tk for v, r, tk in reversed(ticks) if v <= t_ms and r <= t_ms), None)
    n_ev = sum(1 for e in events[:hi] if e["r"] <= t_ms) if count_events else None
    out = {"t_ms": t_ms, "has_book": False, "best_bid": None, "bid_size": None, "best_ask": None, "ask_size": None, "bids_top": [], "asks_top": [],
           "cut_bid": None, "cut_ask": None, "cut_bid_usd": None, "cut_ask_usd": None, "tick": tick, "fee_bps": fee, "last_event_ms": last_v,
           "fresh": bool(last_v is not None and last_v >= t_ms - FRESH_S * 1000), "crossed": False, "n_events": n_ev,
           "book_status": bk.BOOK_OK if book_i is not None else (bk.BOOK_UNAVAILABLE if last_v is not None else bk.NO_EVENTS)}
    if book_i is None:
        return out
    bids, asks = bk._levels(events[book_i]["bids"]), bk._levels(events[book_i]["asks"])
    for e in events[book_i + 1: hi]:
        if e["r"] <= t_ms and e["et"] == "price_change" and e.get("price") is not None:
            side = bids if str(e.get("side")).upper() == "BUY" else asks
            p, s = float(e["price"]), float(e["size"] or 0.0)
            if s <= 0:
                side.pop(p, None)
            else:
                side[p] = s
    bl = sorted(((p, s) for p, s in bids.items() if s > 0), reverse=True)
    al = sorted((p, s) for p, s in asks.items() if s > 0)
    ms = float(min_size) if min_size is not None and math.isfinite(float(min_size)) else None
    out.update(has_book=True, best_bid=bl[0][0] if bl else None, bid_size=bl[0][1] if bl else None, best_ask=al[0][0] if al else None,
               ask_size=al[0][1] if al else None, bids_top=[[p, s] for p, s in bl[:TOP_LEVELS]], asks_top=[[p, s] for p, s in al[:TOP_LEVELS]],
               crossed=bool(bl and al and bl[0][0] >= al[0][0]))
    if ms is not None:
        out["cut_bid"] = next((p for p, s in bl if s >= ms), None)
        out["cut_ask"] = next((p for p, s in al if s >= ms), None)
        out["cut_bid_usd"] = next((p for p, s in bl if s >= ms and s * p >= USD_VARIANT_MIN), None)
        out["cut_ask_usd"] = next((p for p, s in al if s >= ms and s * p >= USD_VARIANT_MIN), None)
    return out


def _js(x) -> str:
    return json.dumps(x, separators=(",", ":"))


def _tick_of(state_tick, frame_tick) -> tuple[float, str]:
    try:
        t = float(state_tick)
        if t > 0:
            return t, "pmxt"
    except (TypeError, ValueError):
        pass
    if frame_tick is not None and math.isfinite(_num(frame_tick)) and _num(frame_tick) > 0:
        return float(frame_tick), "gamma"
    return DEFAULT_TICK, "default"


def day_books(day: str, markets: list[dict], *, fetch, size_fn, gate: Callable[[], None] | None = None,
              meter: Callable[[int], None] | None = None) -> tuple[list[list], list[list], list[list], dict[str, dict], dict]:
    """Origin rows (both tokens at t = d 14:00Z), minute rows (both tokens at u = 14:01..15:00Z) and the hour's ``last_trade_price`` rows of every
    market of ``day``, from the pmxt hour 14Z (cut at 15:00Z) and, only for tokens without a ``book`` event with both clocks <= t there, the 13Z
    lookback (cut at t). A market without any event on either token is ``source_unavailable`` (never "no trade"); one whose outcome-0 token has
    events but no snapshot is ``book_unavailable``. A missing or corrupt 14Z hour raises (the day is unavailable for all its markets)."""
    t0 = int(origin_epoch(day) * 1000)
    end = t0 + 3600 * 1000
    tokens: dict[str, str] = {}
    for m in markets:
        tokens[m["token0"]] = m["condition_id"]
        tokens[m["token1"]] = m["condition_id"]
    ev14, i14 = read_events_kd(bk.hour_dt(day, ORIGIN_HOUR), tokens, fetch=fetch, size_fn=size_fn, cut_ms=end, gate=gate, meter=meter)
    hinfo = {"bytes": i14["bytes"], "row_groups_read": i14["row_groups_read"], "lookback_tokens": 0, "lookback_status": "not_needed"}
    need = {t: c for t, c in tokens.items() if not any(e["et"] == "book" and e["v"] <= t0 and e["r"] <= t0 for e in ev14[t])}
    ev13: dict[str, list[dict]] = {}
    if need:
        hinfo["lookback_tokens"] = len(need)
        try:
            ev13, i13 = read_events_kd(bk.hour_dt(day, LOOKBACK_HOUR), need, fetch=fetch, size_fn=size_fn, cut_ms=t0, gate=gate, meter=meter)
            hinfo["bytes"] += i13["bytes"]
            hinfo["lookback_status"] = "read"
        except (bk.HourMissing, bk.HourCorrupt):
            hinfo["lookback_status"] = "hour_unavailable"
    origins, minutes, ltp = [], [], []
    minfo: dict[str, dict] = {}
    for m in markets:
        mid = m["market_id"]
        ms = _num(m.get("order_min_size"))
        n_tok = {}
        span = 0
        status = "ok"
        for idx in (0, 1):
            tok = m[f"token{idx}"]
            evs = sorted(ev13.get(tok, []) + ev14[tok], key=lambda e: (e["v"], e["r"]))
            n_tok[idx] = len(evs)
            span += sum(1 for e in ev14[tok] if t0 <= e["v"] < end)
            vs = [e["v"] for e in evs]
            ticks = [(e["v"], e["r"], str(e["tick"])) for e in evs if e["et"] == "tick_size_change" and e.get("tick") is not None]
            s = kd_state(evs, t0, min_size=ms, vs=vs, ticks=ticks, count_events=True)
            tick, tsrc = _tick_of(s["tick"], m.get("tick_size"))
            origins.append([mid, day, idx, t0, int(s["has_book"]), int(s["fresh"]), int(s["crossed"]), s["best_bid"], s["bid_size"], s["best_ask"], s["ask_size"],
                            _js(s["bids_top"]), _js(s["asks_top"]), tick, tsrc, s["fee_bps"], s["last_event_ms"], s["n_events"], s["book_status"],
                            "read" if tok in need and hinfo["lookback_status"] == "read" else ("unavailable" if tok in need else "not_needed"), ms if math.isfinite(ms) else ""])
            if idx == 0 and evs and not any(e["et"] == "book" for e in evs):
                status = bk.BOOK_UNAVAILABLE
            if not evs:
                continue
            for k in range(1, N_MINUTES + 1):
                u = t0 + k * 60000
                st = kd_state(evs, u, min_size=ms, vs=vs, ticks=ticks)
                minutes.append([mid, day, idx, k, u, int(st["has_book"]), int(st["fresh"]), int(st["crossed"]), st["best_bid"], st["bid_size"], st["best_ask"],
                                st["ask_size"], st["cut_bid"], st["cut_ask"], st["cut_bid_usd"], st["cut_ask_usd"], st["last_event_ms"], st["book_status"]])
            for e in ev14[tok]:
                if e["et"] == "last_trade_price" and t0 <= e["v"] < end:
                    ltp.append([mid, day, idx, tok, e["v"], e["r"], e.get("price"), e.get("size"), e.get("side"), e.get("tx") or ""])
        if n_tok[0] + n_tok[1] == 0:
            status = "source_unavailable"
        minfo[mid] = {"books_status": status, "n_events_span": span, "n_events_tok0": n_tok[0], "n_events_tok1": n_tok[1],
                      "lookback": "read" if (m["token0"] in need and hinfo["lookback_status"] == "read") else ("unavailable" if m["token0"] in need else "not_needed")}
    return origins, minutes, ltp, minfo, hinfo


def market_day_prints(lim: hb.Limiter, m: dict, day: str, key: bytes, max_pages: int = PRINT_PAGES) -> tuple[list[list], list[list], dict]:
    """Taker prints of one market in ``[t - 6 h, t + 7 h]`` (venue time): (pre rows ``ts < t``, post rows ``ts >= t`` for the guarded file, info). A capped
    window yields no rows and ``info['capped']``. The raw wallet is hashed on parse and is never kept."""
    t = int(origin_epoch(day))
    rows, info = cm.windowed_prints(lim, m["condition_id"], t - PRINT_PRE_S, t + PRINT_POST_S, max_pages, key, limit=PRINT_LIMIT)
    if info["capped"]:
        return [], [], info
    out = []
    for rank_, p in enumerate(rows):
        out.append([m["market_id"], day, p["ts"], p["idx"], m[f"token{p['idx']}"], p["side"], p["price"], p["size"], p["yes_price"], p["yes_side"], p["wallet"] or "",
                    p["tx"], rank_])
    out.sort(key=lambda r: (r[2], -r[12]))
    info["n_span"] = sum(1 for r in out if t <= r[2] < t + 3600)
    return [r for r in out if r[2] < t], [r for r in out if r[2] >= t], info


def day_order(days: list[str], seed: str = SEED_ORDER) -> list[str]:
    return sorted(days, key=lambda d: hb._rank(seed, d))


def _fail_counts(pf: Path) -> dict[tuple[str, str], int]:
    return bk._fail_counts(pf)


def _require_frame(frame_dir: Path) -> dict:
    fman_p = Path(frame_dir) / "manifest.json"
    if not fman_p.exists():
        raise c9.Refused(f"frame run {frame_dir} has no manifest; run kd-frame first")
    fman = json.loads(fman_p.read_text())
    if not (fman.get("complete") is True and fman.get("status") == FRAME_COMPLETE and not fman.get("stopped")):
        raise c9.Refused(f"frame run {Path(frame_dir).name} is not {FRAME_COMPLETE} (status {fman.get('status')})")
    cm.verify_manifest_files(Path(frame_dir), fman)
    return fman


def kd_books(root: Path, transport, *, rules_sha: str, key: bytes, fp: str, fetch, size_fn, ingress_cap_gb: float = INGRESS_CAP_GB, rps: float = MAX_RPS_BOOKS,
             disk_cap: int = int(BOOKS_OUTPUT_CAP_GB * 1024**3), budget_min: float | None = None, data_dumps: Path | None = None,
             data_dumps_cap_gb: float = DATA_DUMPS_CAP_GB, wall_clock: Callable[[], float] = time.time, sleep=time.sleep, live_check=None, health_check=None,
             snapshot_root: Path | None = None, should_stop: Callable[[], bool] | None = None, now: float | None = None, run_id: str = BOOKS_RUN,
             frame_run: str = FRAME_RUN, t_seal_epoch: float = c9.T_SEAL_EPOCH) -> dict:
    """q0186, one resumable chunk. Refusals (run id, root, T_seal, the finished frame run and its file hashes, a sealed run) -> sticky end states ->
    headroom (exit 75) -> per day in seeded order: pmxt states (ingress metered and capped; remaining days unavailable, counted), then prints of every
    market-day; SCREEN and HOLDOUT rows are written to their own directories. Finally ``<split>/markets.csv.gz``, ``days.csv.gz`` and the hashes."""
    root = Path(root)
    c9.refuse_run_id(run_id, BOOKS_RUN)
    c9.refuse_path(root)
    c9.require_after_t_seal(time.time() if now is None else now, "kd-books", t_seal_epoch)
    fdir = root / frame_run
    fman = _require_frame(fdir)
    rdir = root / run_id
    if (rdir / SEAL_NAME).exists():
        raise c9.Refused(f"{run_id} is sealed; kd-books never touches a sealed run")
    done_m = _manifest_done(rdir, (BOOKS_COMPLETE, INGRESS_CAP_STATUS))
    if done_m:
        return {"stopped": None, "status": done_m["status"], "complete": True, "counts": done_m.get("counts")}
    term = cm.prior_terminal(rdir)
    if term:
        return term
    cm.require_room(data_dumps, data_dumps_cap_gb, disk_cap)
    fr = cm.open_run(root, run_id, transport, allowed_run_id=BOOKS_RUN, kind="cb9_kd_books", label="CB9-K/D books",
                     params={"ingress_cap_gb": ingress_cap_gb, "frame_manifest_sha256": h5_seal.sha256_file(fdir / "manifest.json"), "evidence_role": c9.EVIDENCE_ROLE_HIST},
                     rules_sha=rules_sha, key_fp=fp, disk_cap=disk_cap, rps=min(rps, MAX_RPS_BOOKS), budget_min=budget_min, now=now, sleep=sleep,
                     live_check=live_check, wall_clock=wall_clock, snapshot_root=snapshot_root, health_check=health_check)
    fr.extra_state["frame_rules_sha256"] = fman.get("rules_sha256")
    why = fr.unhealthy()
    if why:
        m = fr.manifest(why, {"transient": True})
        m["status"] = "in_progress"
        return m
    cap_bytes = ingress_cap_gb * 1e9
    sample = read_sample(fdir)
    markets_by_day: dict[str, list[dict]] = {}
    for r in sample:
        for d in r["days"]:
            markets_by_day.setdefault(d, []).append(r)
    part, pf = rdir / "days_partial.jsonl.gz", rdir / "days_fail.jsonl"
    try:
        done = {(r["day"], r["stage"]): r for r in c6.iter_partial(part)}
        fails = _fail_counts(pf)
        retry = False
        for d in day_order(list(markets_by_day)):
            mkts = markets_by_day[d]
            for stage in ("books", "prints"):
                if (d, stage) in done:
                    continue
                if stage == "prints" and (d, "books") not in done:  # the books stage is pending a retry: prints wait for it
                    break
                why = fr.stop_reason(should_stop)
                if why:
                    m = fr.manifest(why, {"transient": True})
                    m["status"] = "in_progress"
                    return m
                capped_day = (stage == "books" and bk.ingress_used(rdir) >= cap_bytes) or (stage == "prints" and done[(d, "books")]["status"] == "ingress_cap")
                if capped_day:
                    rec = {"day": d, "stage": stage, "status": "ingress_cap", "markets": {}}
                    c7.append_member(fr, part, rec)
                    done[(d, stage)] = rec
                    fr.counts[f"{stage}_ingress_cap"] = fr.counts.get(f"{stage}_ingress_cap", 0) + 1
                    continue
                try:
                    if stage == "books":
                        o, mi, lt, minfo, hinfo = day_books(d, mkts, fetch=fetch, size_fn=size_fn, meter=lambda n, d=d: bk.ingress_add(rdir, n, f"books:{d}"))
                        split_of = {r["market_id"]: r["split"] for r in mkts}
                        for sp in (SCREEN, HOLDOUT):
                            fr.budget.write_gz_csv(rdir / sp / f"{d}{ORIGINS_SUFFIX}", ORIGIN_COLUMNS, [x for x in o if split_of[x[0]] == sp])
                            fr.budget.write_gz_csv(rdir / sp / f"{d}{MINUTES_SUFFIX}", MINUTE_COLUMNS, [x for x in mi if split_of[x[0]] == sp])
                            fr.budget.write_gz_csv(rdir / sp / f"{d}{LTP_SUFFIX}", LTP_COLUMNS, [x for x in lt if split_of[x[0]] == sp])
                        rec = {"day": d, "stage": stage, "status": "ok", "markets": minfo, "bytes": hinfo["bytes"], "lookback_status": hinfo["lookback_status"]}
                    else:
                        pre, post, minfo = [], [], {}
                        for mrow in mkts:
                            a, b, info = market_day_prints(fr.lim, mrow, d, key)
                            pre += a
                            post += b
                            minfo[mrow["market_id"]] = {"prints_status": "capped" if info["capped"] else "ok", "n_pre": len(a), "n_post": len(b),
                                                        "n_span": info.get("n_span", 0), "pages": info["pages"]}
                        split_of = {r["market_id"]: r["split"] for r in mkts}
                        for sp in (SCREEN, HOLDOUT):
                            fr.budget.write_gz_csv(rdir / sp / f"{d}{PRINTS_PRE_SUFFIX}", PRINT_COLUMNS, [x for x in pre if split_of[x[0]] == sp])
                            fr.budget.write_gz_csv(rdir / sp / f"{d}{PRINTS_POST_SUFFIX}", PRINT_COLUMNS, [x for x in post if split_of[x[0]] == sp])
                        rec = {"day": d, "stage": stage, "status": "ok", "markets": minfo}
                except (bk.HourMissing, bk.HourCorrupt) as exc:
                    rec = {"day": d, "stage": stage, "status": "hour_missing" if isinstance(exc, bk.HourMissing) else "hour_corrupt", "markets": {}}
                except OSError:
                    raise
                except Exception as exc:  # a network / API failure: counted attempts, then "failed" (unavailable, counted)
                    fails[(d, stage)] = fails.get((d, stage), 0) + 1
                    with pf.open("a") as fh:
                        fh.write(json.dumps({"day": d, "stage": stage, "error": f"{type(exc).__name__}: {exc}"[:120]}) + "\n")
                    if fails[(d, stage)] < cm.MAX_ITEM_ATTEMPTS:
                        fr.counts["request_failures"] = fr.counts.get("request_failures", 0) + 1
                        retry = True
                        continue
                    rec = {"day": d, "stage": stage, "status": "failed", "markets": {}}
                c7.append_member(fr, part, rec)
                done[(d, stage)] = rec
                fr.counts[f"{stage}_{rec['status']}"] = fr.counts.get(f"{stage}_{rec['status']}", 0) + 1
        if retry:
            m = fr.manifest("pending_retry", {"transient": True})
            m["status"] = "in_progress"
            return m
        finalize_books(fr, rdir, done, markets_by_day)
    except OSError as exc:
        return cm.disk_budget_end(fr, exc)
    status = INGRESS_CAP_STATUS if any(r["status"] == "ingress_cap" for r in done.values()) else BOOKS_COMPLETE
    m = fr.manifest(None, {"complete": True, "status": status})
    m["status"] = status
    return m


def finalize_books(fr: cm.Cb8Run, rdir: Path, done: dict, markets_by_day: dict[str, list[dict]]) -> None:
    """``<split>/markets.csv.gz`` (per market-day statuses and counts) and ``days.csv.gz`` from the day records, then the hash of every file; the
    partials are dropped last."""
    rows: dict[str, list[list]] = {SCREEN: [], HOLDOUT: []}
    drows = []
    for d in sorted(markets_by_day):
        b, p = done[(d, "books")], done[(d, "prints")]
        for mk_ in sorted(markets_by_day[d], key=lambda x: x["market_id"]):
            mid = mk_["market_id"]
            bi = b["markets"].get(mid) if b["status"] == "ok" else None
            pi = p["markets"].get(mid) if p["status"] == "ok" else None
            rows[mk_["split"]].append([mid, d, mk_["split"], mk_["event_key"], bi["books_status"] if bi else f"day_{b['status']}", (bi or {}).get("lookback", ""),
                                       (bi or {}).get("n_events_span", 0), (bi or {}).get("n_events_tok0", 0), (bi or {}).get("n_events_tok1", 0),
                                       pi["prints_status"] if pi else f"day_{p['status']}", (pi or {}).get("n_pre", 0), (pi or {}).get("n_post", 0),
                                       (pi or {}).get("n_span", 0), (pi or {}).get("pages", 0)])
        drows.append([d, sum(1 for x in markets_by_day[d] if x["split"] == SCREEN), sum(1 for x in markets_by_day[d] if x["split"] == HOLDOUT), b["status"], p["status"],
                      b.get("lookback_status", ""), b.get("bytes", "")])
    for sp in (SCREEN, HOLDOUT):
        fr.budget.write_gz_csv(rdir / sp / MARKETS_FILE, MARKET_DAY_COLUMNS, rows[sp])
    fr.budget.write_gz_csv(rdir / "days.csv.gz", DAY_COLUMNS, drows)
    for p_ in sorted(rdir.rglob("*.csv.gz")):
        fr.record_file(p_)
    if (rdir / "ingress.jsonl").exists():
        fr.record_file(rdir / "ingress.jsonl")
    (rdir / "days_partial.jsonl.gz").unlink(missing_ok=True)
    (rdir / "days_fail.jsonl").unlink(missing_ok=True)


# ---- q0187: the seal --------------------------------------------------------------------------------------------------------------------------


def kd_seal(root: Path, *, rules_sha: str, transport=None, seals_dir: Path | None = None, rps: float = MAX_RPS_SEAL, sleep=time.sleep, live_check=None,
            is_committed: Callable[[Path], bool] | None = None, run_id: str = BOOKS_RUN, frame_run: str = FRAME_RUN) -> dict:
    """q0187. Refuses unless kd-books is finished and every file matches its manifest hash. Seal-time drops (by id and by key, light Gamma lookup)
    against every seal copy committed by now except CB9's own are recorded as ``DROPPED_SEAL_COPIES`` rows in ``drops.csv.gz`` (sealed files are never
    edited). Writes ``holdout_SEAL.json`` (HOLDOUT listing sha256) and the committed copy ``seals/cb9_kd_holdout_SEAL.json`` (never rewritten)."""
    root = Path(root)
    c9.refuse_run_id(run_id, BOOKS_RUN)
    c9.refuse_path(root)
    rdir = root / run_id
    seals_dir = Path(seals_dir or c9.SEALS_DIR)
    seal_p = rdir / SEAL_NAME
    if seal_p.exists():
        doc = json.loads(seal_p.read_text())
        return {"status": SEAL_STATUS, "listing_sha256": doc["listing_sha256"], "already_sealed": True}
    man = json.loads((rdir / "manifest.json").read_text()) if (rdir / "manifest.json").exists() else {}
    if not (man.get("complete") is True and not man.get("stopped") and man.get("status") in (BOOKS_COMPLETE, INGRESS_CAP_STATUS)):
        raise c9.NotNow(f"{run_id} is not finished yet (status {man.get('status')})")
    n_checked = cm.verify_manifest_files(rdir, man)
    _require_frame(root / frame_run)
    ids, used, skipped, shas = bk.seal_copy_ids_audited(seals_dir, own=tuple(c9.OWN_SEAL_COPIES), is_committed=is_committed)
    keys: dict[str, set[str]] = {"event": set(), "neg_risk_market": set(), "series": set()}
    missing_meta = 0
    if ids:
        if transport is None:
            raise c9.Refused("seal copies exist but no transport was given for the key lookup")
        lim = hb.Limiter(transport, rps=min(rps, MAX_RPS_SEAL), sleep=sleep, live_check=live_check)
        found, _ = c6.lookup_keys(lim, sorted(ids))
        missing_meta = len(ids) - len(found)
        for k in found.values():
            keys["event"].update(e for e in str(k.get("event_ids") or "").split(";") if e)
            if k.get("neg_risk_market_id"):
                keys["neg_risk_market"].add(k["neg_risk_market_id"])
            keys["series"].update(s for s in str(k.get("series_ids") or "").split(";") if s)
    unverified = bool(ids) and missing_meta / len(ids) > c9.MAX_UNVERIFIED_KEY_SHARE
    sample = read_sample(root / frame_run)
    rows, n = [], {"KEPT": 0, "DROPPED_SEAL_COPIES": 0}
    for r in sample:
        why = (["id"] if r["market_id"] in ids else []) + c7.key_types_matched(r, keys)
        if why:
            n["DROPPED_SEAL_COPIES"] += 1
            rows.append([r["market_id"], "DROPPED_SEAL_COPIES", "+".join(why)])
        else:
            n["KEPT"] += 1
    rows.sort()
    (rdir / DROPS_FILE).write_bytes(hb._gz_csv_bytes(["market_id", "block", "reason"], rows))
    holdout = {k: v for k, v in h5_seal.list_files(rdir).items() if k.startswith(HOLDOUT + "/")}
    doc = {"seal_version": "cb9-kd-holdout-seal-v1", "run_id": run_id, "sealed_utc": cm.iso(time.time()), "git_commit": hb._git_commit(), "rules_sha256": rules_sha,
           "books_rules_sha256": man.get("rules_sha256"), "wallet_key_fingerprint": man.get("wallet_key_fingerprint"), "books_status": man.get("status"),
           "listing_sha256": h5_seal.listing_sha256(holdout), "n_holdout_files": len(holdout), "files": dict(sorted(holdout.items())), "fetched_files_rehashed": n_checked,
           "drops": {"counts": n, "seal_copies_read": used, "seal_copies_sha256": shas, "seal_copies_skipped": skipped, "drop_ids": len(ids), "drop_ids_without_metadata": missing_meta,
                     "disjointness": UNVERIFIED if unverified else "verified", "drops_sha256": h5_seal.sha256_file(rdir / DROPS_FILE)},
           "frame_market_ids": {s: sorted(r["market_id"] for r in sample if r["split"] == s) for s in (SCREEN, HOLDOUT)},
           "frame_manifest_sha256": h5_seal.sha256_file(root / frame_run / "manifest.json"),
           "read_rules": "verify the listing hash first; append every read to ACCESS_LOG.jsonl; holdout/ is not opened before K1 or D1 advanced and its Stage-1 result is "
                         "recorded; markets in DROPPED_* rows of drops.csv.gz are never analysed",
           "information_end": "every pmxt state at or before d 15:00Z; prints at or before d 21:00Z (t + 7 h); post-origin prints are in *_guarded files"}
    data = json.dumps(doc, indent=1, sort_keys=True).encode()
    dest = seals_dir / SEAL_COPY_NAME
    if dest.exists() and dest.read_bytes() != data:
        raise c9.Refused(f"{dest} exists with different content; a seal is never rewritten")
    seal_p.write_bytes(data)
    (rdir / ACCESS_LOG).touch()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return {"status": SEAL_STATUS, "listing_sha256": doc["listing_sha256"], "committed_copy": str(dest), "drop_counts": n, "disjointness": doc["drops"]["disjointness"],
            "n_holdout_files": len(holdout)}


def verify_holdout_seal(rdir: Path, seals_dir: Path | None = None) -> dict:
    """The HOLDOUT listing equals the seal and the committed copy equals the run's seal file. Any difference is a refusal."""
    rdir = Path(rdir)
    sp = rdir / SEAL_NAME
    if not sp.exists():
        raise c9.Refused(f"{rdir.name} has no {SEAL_NAME}; run kd-seal first")
    doc = json.loads(sp.read_text())
    copy = Path(seals_dir or c9.SEALS_DIR) / SEAL_COPY_NAME
    if not copy.exists() or copy.read_bytes() != sp.read_bytes():
        raise c9.Refused(f"seal copy {copy} missing or different from {sp}")
    holdout = {k: v for k, v in h5_seal.list_files(rdir).items() if k.startswith(HOLDOUT + "/")}
    if h5_seal.listing_sha256(holdout) != doc["listing_sha256"]:
        raise c9.Refused("HOLDOUT listing sha256 differs from the seal; refusing")
    return doc


# ---- analysis: guarded loading ------------------------------------------------------------------------------------------------------------------


def _guard_split(split: str, job: str) -> None:
    if split not in (SCREEN, HOLDOUT):
        raise c9.Refused(f"unknown split {split!r}")
    if split == HOLDOUT and job != "rep":
        raise c9.Refused("HOLDOUT is sealed: only rep-kd opens it, after K1 or D1 advanced and its Stage-1 result is recorded")


def _guard_post(job: str) -> None:
    if job not in ("screen", "rep"):
        raise c9.Refused(f"guarded post-origin prints are opened only by screen-kd and rep-kd (job {job!r})")


def dropped_ids(rdir: Path) -> set[str]:
    p = Path(rdir) / DROPS_FILE
    if not p.exists():
        raise c9.Refused(f"{p} not found: the seal step (kd-seal) has not run")
    return {r["market_id"] for r in c7.read_csv_gz(p) if str(r.get("block", "")).startswith("DROPPED")}


def _f(x) -> float:
    if x is None or x == "":
        return math.nan
    try:
        return float(x)
    except (TypeError, ValueError):
        return math.nan


def _print_arrays(rows: list[dict]) -> dict[str, np.ndarray]:
    rows = sorted(rows, key=lambda r: (int(r["ts"]), -int(r["api_rank"])))
    return {"ts": np.array([float(r["ts"]) for r in rows]), "idx": np.array([int(r["idx"]) for r in rows], dtype=int),
            "price": np.array([float(r["price"]) for r in rows]), "size": np.array([float(r["size"]) for r in rows]),
            "yes_price": np.array([float(r["yes_price"]) for r in rows]), "yes_side": np.array([int(r["yes_side"]) for r in rows], dtype=int),
            "tx": np.array([r["tx"] for r in rows], dtype=object), "api_rank": np.array([int(r["api_rank"]) for r in rows], dtype=int)}


def _group_rows(path: Path) -> dict[tuple[str, str], list[dict]]:
    out: dict[tuple[str, str], list[dict]] = {}
    if Path(path).exists():
        for r in c7.read_csv_gz(path):
            out.setdefault((r["market_id"], r["day"]), []).append(r)
    return out


def _log_access(rdir: Path, job: str, files: list[str]) -> None:
    with (Path(rdir) / ACCESS_LOG).open("a") as fh:
        fh.write(json.dumps({"utc": cm.iso(time.time()), "job": job, "files": files}) + "\n")


class CountOnlyPosts:
    """Census accessor over one market-day's guarded post-origin prints. It answers only yes / no and count questions (a quote filled under a rule,
    a mark available, a next transaction within 10 minutes, prints in a span); no price, mark, fill price or mark-out ever leaves it."""

    __slots__ = ("_a",)

    def __init__(self, rows: list[dict]) -> None:
        self._a = _print_arrays(rows)

    def quote_filled(self, t: float, side: str, price: float, depth: float, *, rule: str = "queue", t_from: float | None = None) -> bool:
        return bool(_fill(self._a, t, side, price, depth, rule=rule, t_from=t_from))

    def mark_available(self, t: float) -> bool:
        return bool(math.isfinite(mark_value(self._a, t)))

    def next_tx_exists(self, u: float, idx: int = 0) -> bool:
        return next_tx(self._a, u, idx) is not None

    def n_between(self, a: float, b: float) -> int:
        ts = self._a["ts"]
        return int(((ts >= a) & (ts < b)).sum())


def load_units(root: Path, split: str, *, job: str, frame_run: str = FRAME_RUN, run_id: str = BOOKS_RUN) -> list[dict]:
    """Per market-day units of ``split``: frame fields, the outcome-0 origin state, the outcome-0 minute states, the pre-origin prints (arrays) and the
    post-origin prints (arrays for ``screen`` / ``rep``; a :class:`CountOnlyPosts` for ``census``). Markets in seal-time drop rows are excluded."""
    _guard_split(split, job)
    root = Path(root)
    rdir = root / run_id
    sdir = rdir / split
    sample = {r["market_id"]: r for r in read_sample(root / frame_run)}
    drop = dropped_ids(rdir)
    md = [r for r in c7.read_csv_gz(sdir / MARKETS_FILE) if r["market_id"] not in drop]
    if split == HOLDOUT:
        _log_access(rdir, job, sorted(p.relative_to(rdir).as_posix() for p in sdir.glob("*")))
    by_day: dict[str, list[dict]] = {}
    for r in md:
        by_day.setdefault(r["day"], []).append(r)
    units = []
    for d in sorted(by_day):
        origins = _group_rows(sdir / f"{d}{ORIGINS_SUFFIX}")
        minutes = _group_rows(sdir / f"{d}{MINUTES_SUFFIX}")
        pre = _group_rows(sdir / f"{d}{PRINTS_PRE_SUFFIX}")
        if job in ("screen", "rep"):
            _guard_post(job)
        post = _group_rows(sdir / f"{d}{PRINTS_POST_SUFFIX}")
        for r in by_day[d]:
            k = (r["market_id"], d)
            s = sample.get(r["market_id"], {})
            o0 = next((x for x in origins.get(k, []) if x["idx"] == "0"), None)
            mins = sorted((x for x in minutes.get(k, []) if x["idx"] == "0"), key=lambda x: int(x["minute"]))
            prints_ok = r["prints_status"] == "ok"
            units.append({"market_id": r["market_id"], "day": d, "month": d[:7], "event": r["event_key"], "t": origin_epoch(d), "md": r, "origin": o0, "minutes": mins,
                          "fee_category": s.get("fee_category", ""), "liquidity": s.get("liquidity", math.nan), "min_size": s.get("order_min_size", math.nan),
                          "prints_ok": prints_ok, "pre": _print_arrays(pre.get(k, [])) if prints_ok else None,
                          "post": (_print_arrays(post.get(k, [])) if job in ("screen", "rep") else CountOnlyPosts(post.get(k, []))) if prints_ok else None})
    return units


# ---- K: features, cells, quotes, fills, marks -------------------------------------------------------------------------------------------------------


def two_sided_fresh(o: dict | None) -> bool:
    if not o or o.get("has_book") != "1" or o.get("fresh") != "1" or o.get("crossed") == "1":
        return False
    return math.isfinite(_f(o.get("best_bid"))) and math.isfinite(_f(o.get("best_ask")))


def x6_feature(pre: dict[str, np.ndarray] | None, t: float) -> float:
    """HB2's frozen x6: notional imbalance (YES terms, own-token notional size x price) over prints in [t - 6 h, t), clipped and scaled."""
    if pre is None or not len(pre["ts"]):
        return math.nan
    m = (pre["ts"] >= t - X6_WINDOW_S) & (pre["ts"] < t)
    n = pre["size"][m] * pre["price"][m]
    tot = float(n.sum())
    if tot <= 0:
        return math.nan
    f = float((pre["yes_side"][m] * n).sum()) / tot
    return float(np.clip(f, -X6_CLIP, X6_CLIP) / X6_SD)


def rv_feature(pre: dict[str, np.ndarray] | None, t: float) -> float:
    """log(RV + 1e-4): RMS of consecutive differences of the last-print YES price on a 600 s grid over [t - RV_WINDOW_S, t) (prints with ts <= grid point
    and < t); NaN with fewer than 3 differences (the h2 ``ml_rv_1d`` analogue on prints)."""
    if pre is None or not len(pre["ts"]):
        return math.nan
    m = pre["ts"] < t
    ts, yp = pre["ts"][m], pre["yes_price"][m]
    grid = np.arange(t - RV_WINDOW_S, t, RV_GRID_S, dtype=float)
    pos = np.searchsorted(ts, grid, side="right") - 1
    vals = np.where(pos >= 0, yp[np.clip(pos, 0, None)] if len(yp) else np.nan, np.nan)
    d = np.diff(vals)
    d = d[np.isfinite(d)]
    if len(d) < RV_MIN_DIFFS:
        return math.nan
    return float(np.log(math.sqrt(float((d**2).mean())) + RV_EPS))


def k_features(u: dict) -> dict:
    o = u["origin"]
    ok = two_sided_fresh(o) and u["prints_ok"]
    bb, ba = (_f(o.get("best_bid")), _f(o.get("best_ask"))) if o else (math.nan, math.nan)
    return {"eligible": bool(ok), "x6": x6_feature(u["pre"], u["t"]) if ok else math.nan, "rv": rv_feature(u["pre"], u["t"]) if ok else math.nan,
            "spr": (ba - bb) if ok else math.nan}


def k_cuts(feats: list[dict]) -> dict:
    """SCREEN cut points from feature values only: RV and SPR top-tercile cuts over eligible origins, then the median |x6| over eligible cell origins."""
    el = [f for f in feats if f["eligible"]]
    rv = np.array([f["rv"] for f in el if math.isfinite(f["rv"])])
    sp = np.array([f["spr"] for f in el if math.isfinite(f["spr"])])
    cuts = {"rv": float(np.quantile(rv, CELL_QUANTILE)) if len(rv) else math.nan, "spr": float(np.quantile(sp, CELL_QUANTILE)) if len(sp) else math.nan}
    ax = np.array([abs(f["x6"]) for f in el if in_cell(f, cuts) and math.isfinite(f["x6"])])
    cuts["x6_abs"] = float(np.quantile(ax, SKEW_QUANTILE)) if len(ax) else math.nan
    cuts["n_rv"], cuts["n_spr"], cuts["n_x6"] = int(len(rv)), int(len(sp)), int(len(ax))
    return cuts


def in_cell(f: dict, cuts: dict) -> bool:
    if not f["eligible"]:
        return False
    a = math.isfinite(f["rv"]) and math.isfinite(cuts["rv"]) and f["rv"] >= cuts["rv"]
    b = math.isfinite(f["spr"]) and math.isfinite(cuts["spr"]) and f["spr"] >= cuts["spr"]
    return bool(a or b)


def skew_dir(f: dict, cuts: dict) -> int:
    x = f["x6"]
    if not (math.isfinite(x) and math.isfinite(cuts["x6_abs"])) or abs(x) < cuts["x6_abs"] or x == 0:
        return 0
    return 1 if x > 0 else -1


def quote_prices(bb: float, ba: float, tick: float, s: int) -> tuple[float, float]:
    """(bid, ask) of the touch maker (``s`` = 0) or the skewed maker (``s`` = +1 / -1, one tick in the flow direction). An improving quote stays strictly
    inside the spread (else the touch); a worsening one stays within [tick, 1 - tick] (else the touch)."""
    step = SKEW_TICKS * tick
    if s == 0:
        return bb, ba
    if s > 0:
        bid = bb + step if bb + step < ba - 1e-9 else bb
        ask = ba + step if ba + step <= 1.0 - tick + 1e-9 else ba
    else:
        ask = ba - step if ba - step > bb + 1e-9 else ba
        bid = bb - step if bb - step >= tick - 1e-9 else bb
    return round(bid, 6), round(ask, 6)


def level_depth(levels: list, price: float, side: str) -> float:
    """Displayed size at ``price`` on one side (top 10 levels of the origin state). An absent level inside the stored range (or with fewer than 10 stored
    levels) has depth 0; one beyond the stored range is unknown (inf: never filled, the conservative reading)."""
    for p, s in levels:
        if abs(float(p) - price) < 1e-9:
            return float(s)
    if len(levels) < TOP_LEVELS or not levels:
        return 0.0
    worst = float(levels[-1][0])
    inside = price > worst - 1e-9 if side == "bid" else price < worst + 1e-9
    return 0.0 if inside else math.inf


def _pr(a: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    return {"ts": a["ts"], "p0": a["yes_price"], "buy": a["yes_side"] == 1, "size": a["size"]}


def _fill(a: dict[str, np.ndarray], t: float, side: str, price: float, depth: float, *, rule: str = "queue", t_from: float | None = None) -> bool:
    """One resting quote over (t_from, t + life): ``queue`` = ``cb3_maker.quote_fills`` queue rule (own 50); ``through`` = cumulative opposite-aggressor
    volume strictly through the price reaches 50 (the binding worst-case bracket)."""
    if not math.isfinite(depth):
        return False
    start = t if t_from is None else t_from
    life = QUOTE_LIFE_S - (start - t)
    if rule == "queue":
        return mk.quote_fills(_pr(a), start, side, price, depth, life=life, own=QUOTE_SHARES)["queue"][0] == 1
    ts = a["ts"]
    lo, hi = np.searchsorted(ts, start, side="right"), np.searchsorted(ts, start + life, side="left")
    if side == "bid":
        ok = (a["yes_side"][lo:hi] == -1) & (a["yes_price"][lo:hi] < price - 1e-9)
    else:
        ok = (a["yes_side"][lo:hi] == 1) & (a["yes_price"][lo:hi] > price + 1e-9)
    return bool(a["size"][lo:hi][ok].sum() >= QUOTE_SHARES - 1e-12)


def mark_value(a: dict[str, np.ndarray], t: float) -> float:
    """Mid of the last taker-BUY and last taker-SELL YES prices in [t + 5 h, t + 7 h]; NaN unless both exist."""
    ts = a["ts"]
    m = (ts >= t + MARK_FROM_S) & (ts <= t + MARK_TO_S)
    if not m.any():
        return math.nan
    ys, yp = a["yes_side"][m], a["yes_price"][m]
    b, s = np.flatnonzero(ys == 1), np.flatnonzero(ys == -1)
    if not len(b) or not len(s):
        return math.nan
    return float((yp[b[-1]] + yp[s[-1]]) / 2.0)


def _origin_book(u: dict) -> tuple[float, float, float, list, list, float]:
    o = u["origin"]
    tick = _f(o.get("tick"))
    tick = tick if math.isfinite(tick) and tick > 0 else DEFAULT_TICK
    return _f(o["best_bid"]), _f(o["best_ask"]), tick, json.loads(o.get("bids_top") or "[]"), json.loads(o.get("asks_top") or "[]"), _f(o.get("fee_bps"))


def quote_result(u: dict, s: int, *, rule: str = "queue", latency: float = 0.0, worst_case: bool = False, cache: dict | None = None) -> dict:
    if cache is not None:
        ck = (u["market_id"], u["day"], s, rule, latency, worst_case)
        if ck not in cache:
            cache[ck] = _quote_result(u, s, rule=rule, latency=latency, worst_case=worst_case)
        return cache[ck]
    return _quote_result(u, s, rule=rule, latency=latency, worst_case=worst_case)


def _quote_result(u: dict, s: int, *, rule: str = "queue", latency: float = 0.0, worst_case: bool = False) -> dict:
    """Fills and mark-outs (cents per filled share) of one quote type at one origin. Unavailable mark: mark-out NaN (or -1 tick per filled share under
    ``worst_case``). ``net_c`` is the origin's mark-out P&L per posted share (100 shares; unfilled = 0)."""
    bb, ba, tick, bids, asks, fee = _origin_book(u)
    bid, ask = quote_prices(bb, ba, tick, s)
    a, t = u["post"], u["t"]
    M = mark_value(a, t)
    fills, mos, reb = 0, [], []
    for side, p, lv in (("bid", bid, bids), ("ask", ask, asks)):
        if not _fill(a, t, side, p, level_depth(lv, p, side), rule=rule, t_from=t + latency if latency else None):
            continue
        fills += 1
        if math.isfinite(M):
            mos.append(100.0 * ((M - p) if side == "bid" else (p - M)))
        elif worst_case:
            mos.append(-100.0 * tick)
        r = (fee / 1e4) if math.isfinite(fee) else 0.0
        reb.append(100.0 * mk.rebate_share(u["fee_category"]) * r * p * (1.0 - p))
    have = math.isfinite(M) or worst_case
    mo = float(np.mean(mos)) if (fills and have) else math.nan
    net = (sum(mos) * QUOTE_SHARES / POSTED_SHARES) if have else math.nan
    return {"fills": fills, "mo_c": mo, "net_c": net, "mark_ok": bool(math.isfinite(M)), "rebate_c": float(np.mean(reb)) if reb else 0.0, "bid": bid, "ask": ask}


def k_census_counts(units: list[dict], cuts: dict) -> dict:
    """K census counts (no price beyond the origin book; post prints only through :class:`CountOnlyPosts`)."""
    n = {"origins": len(units), "prints_unavailable": 0, "two_sided_fresh": 0, "cell": 0, "no_skew_excluded": 0, "after_cut": 0, "after_cut_mark_available": 0,
         "filled_origins": {"unskewed": 0, "skewed": 0}}
    events, days = set(), set()
    for u in units:
        f = u.get("_feat") or k_features(u)
        if not u["prints_ok"]:
            n["prints_unavailable"] += 1
        if not f["eligible"]:
            continue
        n["two_sided_fresh"] += 1
        if not in_cell(f, cuts):
            continue
        n["cell"] += 1
        s = skew_dir(f, cuts)
        if s == 0:
            n["no_skew_excluded"] += 1
            continue
        n["after_cut"] += 1
        post: CountOnlyPosts = u["post"]
        if not post.mark_available(u["t"]):
            continue
        n["after_cut_mark_available"] += 1
        events.add(u["event"])
        days.add(u["day"])
        bb, ba, tick, bids, asks, _fee_ = _origin_book(u)
        for name, sd in (("unskewed", 0), ("skewed", s)):
            bid, ask = quote_prices(bb, ba, tick, sd)
            if post.quote_filled(u["t"], "bid", bid, level_depth(bids, bid, "bid")) or post.quote_filled(u["t"], "ask", ask, level_depth(asks, ask, "ask")):
                n["filled_origins"][name] += 1
    n["events"], n["days"] = len(events), len(days)
    gate = {"cell_origins": n["after_cut_mark_available"] >= GK["cell_origins"],
            "filled_origins_per_type": min(n["filled_origins"].values()) >= GK["filled_origins_per_type"],
            "events": n["events"] >= GK["events"], "days": n["days"] >= GK["days"]}
    n["gate_gk"] = {**gate, "pass": all(gate.values()), "thresholds": GK, "counted_on": "units entering K1 (after the skew cut, mark available)"}
    nS, nU = n["filled_origins"]["skewed"], n["filled_origins"]["unskewed"]
    n["mde_c"] = (MDE_Z * K_MARKOUT_SD_C * math.sqrt(K_DEFF * (1.0 / nS + 1.0 / nU))) if nS and nU else None
    return n


# ---- K1 estimators --------------------------------------------------------------------------------------------------------------------------------


def _single(m: np.ndarray, f: np.ndarray) -> tuple[float, np.ndarray | None]:
    N, k = len(m), int(f.sum())
    if not k:
        return math.nan, None
    est = float(m[f].mean())
    return est, est + (N / k) * np.where(f, m - est, 0.0)


def contrast(mS: np.ndarray, fS: np.ndarray, mU: np.ndarray, fU: np.ndarray) -> tuple[float, np.ndarray | None]:
    """K1 = mean over origins with a skewed fill of the skewed mark-out minus the same for unskewed; unit values by the delta method (origins equally
    weighted): v_i = K1 + (N / n_S) 1{S_i}(m_S,i - mean_S) - (N / n_U) 1{U_i}(m_U,i - mean_U); mean(v) = K1."""
    eS, vS = _single(mS, fS)
    eU, vU = _single(mU, fU)
    if vS is None or vU is None:
        return math.nan, None
    return eS - eU, vS - vU


def _k_rows(units: list[dict], cuts: dict, *, cell: bool = True, sign_override: dict | None = None, rule: str = "queue", latency: float = 0.0,
            worst_case: bool = False, cache: dict | None = None) -> list[dict]:
    """K1 rows: eligible origins in (``cell`` = True) or outside the cell, after the skew cut, with a mark (all, under ``worst_case``)."""
    out = []
    for u in units:
        f = u["_feat"]
        if not f["eligible"] or in_cell(f, cuts) != cell:
            continue
        s = skew_dir(f, cuts)
        if s == 0:
            continue
        if sign_override is not None:
            s = sign_override[(u["market_id"], u["day"])]
        U = quote_result(u, 0, rule=rule, latency=latency, worst_case=worst_case, cache=cache)
        S = quote_result(u, s, rule=rule, latency=latency, worst_case=worst_case, cache=cache)
        if not (U["mark_ok"] or worst_case):
            continue
        out.append({"event": u["event"], "day": u["day"], "month": u["month"], "key": (u["market_id"], u["day"]), "U": U, "S": S})
    return out


def _k_arrays(rows: list[dict]) -> dict:
    g = lambda q, k: np.array([r[q][k] for r in rows], float)  # noqa: E731
    return {"mS": np.nan_to_num(g("S", "mo_c")), "fS": g("S", "fills") > 0, "mU": np.nan_to_num(g("U", "mo_c")), "fU": g("U", "fills") > 0,
            "netS": np.nan_to_num(g("S", "net_c")), "rbS": g("S", "rebate_c"), "rbU": g("U", "rebate_c"), "nS": g("S", "fills"), "nU": g("U", "fills"),
            "event": np.array([r["event"] for r in rows], object), "day": np.array([r["day"] for r in rows], object), "month": np.array([r["month"] for r in rows], object)}


def _clusters(ar: dict, mask: np.ndarray | None = None) -> dict[str, np.ndarray]:
    if mask is None:
        return {"event": ar["event"], "day": ar["day"]}
    return {"event": ar["event"][mask], "day": ar["day"][mask]}


def route_gate(mS: np.ndarray, fS: np.ndarray, netS: np.ndarray) -> dict:
    """Binding route gate (round 1 item 5) at the point estimate: the skewed maker needs (a) mean mark-out per filled share > 0 (origins with a skewed fill,
    fill-weighted within origin) AND (b) mean net per origin > 0 (each origin's mark-out P&L / 100 posted shares, unfilled = 0, origins equally weighted)."""
    per_fill = float(np.asarray(mS, float)[np.asarray(fS, bool)].mean()) if np.asarray(fS, bool).any() else math.nan
    per_origin = float(np.asarray(netS, float).mean()) if len(netS) else math.nan
    return {"skewed_per_filled_share_c": per_fill, "skewed_net_per_origin_c": per_origin,
            "pass": bool(math.isfinite(per_fill) and math.isfinite(per_origin) and per_fill > 0 and per_origin > 0)}


def k1_stat(rows: list[dict]) -> dict:
    ar = _k_arrays(rows)
    est, v = contrast(ar["mS"], ar["fS"], ar["mU"], ar["fU"])
    if v is None:
        return {"n": len(rows), "effect_c": math.nan, "p": 1.0, "testable": False}
    cp = c9.cluster_p(v, _clusters(ar))
    return {"n": len(rows), "effect_c": est, "p": cp["p"], "testable": cp["testable"], "ways": cp["ways"], "n_filled": {"skewed": int(ar["fS"].sum()), "unskewed": int(ar["fU"].sum())}}


def k1_analysis(units: list[dict], cuts: dict, *, gate_ok: bool, labels: dict, seed: int = c9.PLACEBO_SEEDS["K1_skew_sign"], n_draws: int = c9.PLACEBO_DRAWS,
                alpha: float = c9.GATE_P) -> dict:
    """K1 with the route gate, kill 2, the binding placebo (random skew sign per market x day), the cell attribution, the binding robustness and the
    reported variants. ``alpha`` is the decision level (Stage 1: 0.01; Stage 2: 0.05 / k)."""
    cache: dict = {}
    rows = _k_rows(units, cuts, cache=cache)
    main = k1_stat(rows)
    ar = _k_arrays(rows) if rows else None
    res: dict = {"test": "K1", "unit": "cell origin after the skew cut with a mark", "n_units": len(rows), "estimate": main, "floor_c": K1_FLOOR_C, "alpha": alpha}
    if not gate_ok or not rows or not main["testable"]:
        res.update(testable=False, p=1.0, advance=False, verdict=labels.get("k_gate_label") or "not testable", s0b_label=labels.get("s0b_label"))
        return res
    est = main["effect_c"]
    eS, vS = _single(ar["mS"], ar["fS"])
    eU, vU = _single(ar["mU"], ar["fU"])
    pU = c9.cluster_p(vU, _clusters(ar))["p"] if vU is not None else 1.0
    route = route_gate(ar["mS"], ar["fS"], ar["netS"])
    kill2 = bool(math.isfinite(eU) and eU >= KILL2_FLOOR_C and pU < alpha)
    # placebo: random skew sign per market x day
    rng = np.random.default_rng(seed)
    keys = sorted({r["key"] for r in rows})
    draws = []
    for _ in range(n_draws):
        sg = dict(zip(keys, np.where(rng.random(len(keys)) < 0.5, 1, -1).tolist(), strict=True))
        pr = _k_rows(units, cuts, sign_override=sg, cache=cache)
        draws.append(k1_stat(pr)["p"] if pr else 1.0)
    plc = c9.placebo_advance_rate(draws, alpha)
    # cell attribution
    rest = k1_stat(_k_rows(units, cuts, cell=False, cache=cache))
    credit = bool(math.isfinite(rest["effect_c"]) and est - rest["effect_c"] >= abs(est) / 2.0)
    # robustness
    rob: dict = {}
    tt = k1_stat(_k_rows(units, cuts, rule="through", cache=cache))
    rob["cost_trade_through"] = {"effect_c": tt["effect_c"], "holds": bool(math.isfinite(tt["effect_c"]) and np.sign(tt["effect_c"]) == np.sign(est) and abs(tt["effect_c"]) >= abs(est) / 2.0)}
    _est, v = contrast(ar["mS"], ar["fS"], ar["mU"], ar["fU"])
    top = {}
    for way in ("event", "day"):
        keep = c9.top_k_drop_mask(v, ar[way])
        sub = {k: (x[keep] if isinstance(x, np.ndarray) else x) for k, x in ar.items()}
        e2, v2 = contrast(sub["mS"], sub["fS"], sub["mU"], sub["fU"])
        p2 = c9.cluster_p(v2, _clusters(sub))["p"] if v2 is not None else 1.0
        top[way] = {"effect_c": e2, "p": p2, "holds": bool(v2 is not None and p2 < alpha and e2 >= K1_FLOOR_C)}
    rob["top5_drops"] = {**top, "holds": all(x["holds"] for x in top.values())}
    pooledS = float((ar["mS"] * ar["nS"]).sum() / ar["nS"][ar["fS"]].sum()) if ar["fS"].any() else math.nan
    pooledU = float((ar["mU"] * ar["nU"]).sum() / ar["nU"][ar["fU"]].sum()) if ar["fU"].any() else math.nan
    rob["size_weighted"] = {"effect_c": pooledS - pooledU, "holds": bool(np.sign(pooledS - pooledU) == np.sign(est))}
    months = {}
    for mo in sorted(set(ar["month"])):
        msk = ar["month"] == mo
        nf = int(ar["nS"][msk].sum() + ar["nU"][msk].sum())
        if nf < K_MONTH_MIN_FILLS:
            continue
        e3, _ = contrast(ar["mS"][msk], ar["fS"][msk], ar["mU"][msk], ar["fU"][msk])
        months[mo] = {"fills": nf, "effect_c": e3, "same_sign": bool(math.isfinite(e3) and np.sign(e3) == np.sign(est))}
    rob["months"] = {"months": months, "holds": bool(months) and sum(m["same_sign"] for m in months.values()) >= (2.0 / 3.0) * len(months),
                     "unknown": not months}
    wc = k1_stat(_k_rows(units, cuts, worst_case=True, cache=cache))
    rob["worst_case_marks"] = {"effect_c": wc["effect_c"], "p": wc["p"], "holds": bool(np.sign(wc["effect_c"]) == np.sign(est) and wc["p"] < alpha)}
    lat = k1_stat(_k_rows(units, cuts, latency=LATENCY_S, cache=cache))
    rob["latency"] = {"effect_c": lat["effect_c"], "holds": bool(math.isfinite(lat["effect_c"]) and np.sign(lat["effect_c"]) == np.sign(est) and abs(lat["effect_c"]) >= abs(est) / 2.0)}
    rob_ok = all(x["holds"] for x in rob.values())
    advance = bool(main["p"] < alpha and est >= K1_FLOOR_C and plc["holds"] and rob_ok and route["pass"] and not kill2)
    if kill2:
        verdict = "CB3-B's maker result; skew not needed"
    elif advance:
        verdict = "advance" + ("" if credit else " (skew helps in every cell: cell attribution failed)")
    elif main["p"] < alpha and est >= K1_FLOOR_C and not route["pass"]:
        verdict = "skew helps, but the maker still loses: no route"
    else:
        verdict = f"not detected at MDE {labels.get('k_mde_c')}" if main["p"] >= alpha else "no advance (placebo, robustness or floor)"
    res.update(testable=True, p=main["p"], effect=est, advance=advance, verdict=verdict, route_gate=route, kill2={"unskewed_c": eU, "p": pU, "fires": kill2},
               placebo={"note": "K1 skew-sign calibration (random sign per market x day)", **plc, "seed": seed}, cell_attribution={"k1_rest": rest, "credit": credit},
               robustness=rob, robustness_holds=rob_ok, reported={"rebate_version_c": float((ar["mS"] + ar["rbS"])[ar["fS"]].mean() - (ar["mU"] + ar["rbU"])[ar["fU"]].mean()),
                                                                   "fill_rate": {"skewed": float(ar["fS"].mean()), "unskewed": float(ar["fU"].mean())},
                                                                   "net_per_posted_share_c": {"skewed": float(ar["netS"].mean())}},
               s0b_label=labels.get("s0b_label"))
    return res


# ---- D: dust units and next transactions --------------------------------------------------------------------------------------------------------


def next_tx(a: dict[str, np.ndarray] | None, u: float, idx: int = 0) -> dict | None:
    """The first transaction hash among prints of token ``idx`` with ts in [u + 1 s, u + 600 s] (ties: earliest ts, then oldest in API order); P = the
    size-weighted VWAP of ALL of that transaction's prints on the token; the last fill (newest in API order) is a variant. Never uses ``side``."""
    if a is None or not len(a["ts"]):
        return None
    m = (a["idx"] == idx) & (a["ts"] >= u + NEXT_TX_FROM_S) & (a["ts"] <= u + NEXT_TX_TO_S)
    if not m.any():
        return None
    cand = np.flatnonzero(m)
    order = sorted(cand, key=lambda i: (a["ts"][i], -a["api_rank"][i]))
    tx = a["tx"][order[0]]
    if not tx:
        return None
    mine = np.flatnonzero((a["tx"] == tx) & (a["idx"] == idx))
    sz, px = a["size"][mine], a["price"][mine]
    if sz.sum() <= 0:
        return None
    last = mine[np.argmin(a["api_rank"][mine])]
    return {"tx": tx, "vwap": float((px * sz).sum() / sz.sum()), "last": float(a["price"][last]), "size": float(sz.sum()), "n_prints": int(len(mine))}


def minute_ok(r: dict) -> bool:
    return r.get("has_book") == "1" and r.get("fresh") == "1" and r.get("crossed") != "1" and math.isfinite(_f(r.get("best_bid"))) and math.isfinite(_f(r.get("best_ask")))


def is_dust(r: dict, min_size: float, *, usd: bool = False) -> bool:
    bs, as_ = _f(r.get("bid_size")), _f(r.get("ask_size"))
    d = bs < min_size or as_ < min_size
    if usd:
        d = d or bs * _f(r.get("best_bid")) < USD_VARIANT_MIN or as_ * _f(r.get("best_ask")) < USD_VARIANT_MIN
    return bool(d)


def dust_units(u: dict, *, usd: bool = False) -> tuple[list[dict], dict]:
    """Dust units of one market-day (outcome-0 token): two-sided fresh minutes in dust state, thinned to one unit per episode per 5 minutes (the first).
    Returns (units with m_d, m_c, minute; counts)."""
    ms = u["min_size"]
    c = {"two_sided_minutes": 0, "dust_minutes": 0, "min_size_missing": 0, "units": 0, "mc_unavailable": 0}
    out = []
    if not math.isfinite(ms):
        c["min_size_missing"] = 1
        return out, c
    ep_start = None
    prev_minute = None
    for r in u["minutes"]:
        k = int(r["minute"])
        ok = minute_ok(r)
        if ok:
            c["two_sided_minutes"] += 1
        dust = ok and is_dust(r, ms, usd=usd)
        if not dust:
            ep_start = None
            prev_minute = k
            continue
        c["dust_minutes"] += 1
        if ep_start is None or prev_minute != k - 1:
            ep_start = k
        prev_minute = k
        if (k - ep_start) % EPISODE_STEP_MIN != 0:
            continue
        c["units"] += 1
        cb, ca = (_f(r.get("cut_bid_usd")), _f(r.get("cut_ask_usd"))) if usd else (_f(r.get("cut_bid")), _f(r.get("cut_ask")))
        if not (math.isfinite(cb) and math.isfinite(ca)):
            c["mc_unavailable"] += 1
            continue
        out.append({"minute": k, "u": int(r["u_ms"]) / 1000.0, "m_d": (_f(r["best_bid"]) + _f(r["best_ask"])) / 2.0, "m_c": (cb + ca) / 2.0})
    return out, c


def d_census_counts(units: list[dict]) -> dict:
    n = {"market_days": len(units), "two_sided_minutes": 0, "dust_minutes": 0, "min_size_missing_market_days": 0, "dust_units": 0, "mc_unavailable": 0,
         "units_with_next_tx": 0, "units_without_next_tx": 0, "market_days_with_units": 0, "market_days_with_two_sided": 0, "market_days_with_dust": 0}
    for u in units:
        du, c = dust_units(u)
        n["two_sided_minutes"] += c["two_sided_minutes"]
        n["dust_minutes"] += c["dust_minutes"]
        n["min_size_missing_market_days"] += c["min_size_missing"]
        n["dust_units"] += c["units"]
        n["mc_unavailable"] += c["mc_unavailable"]
        n["market_days_with_two_sided"] += int(c["two_sided_minutes"] > 0)
        n["market_days_with_dust"] += int(c["dust_minutes"] > 0)
        k = 0
        if u["prints_ok"]:
            for x in du:
                if u["post"].next_tx_exists(x["u"]):
                    k += 1
        n["units_with_next_tx"] += k
        n["units_without_next_tx"] += len(du) - k
        n["market_days_with_units"] += int(k > 0)
    share = n["dust_minutes"] / n["two_sided_minutes"] if n["two_sided_minutes"] else 0.0
    n["dust_share_minutes"] = share
    n["dust_share_market_hours"] = n["market_days_with_dust"] / n["market_days_with_two_sided"] if n["market_days_with_two_sided"] else 0.0
    gate = {"dust_share": share >= GD["dust_share"], "units": n["units_with_next_tx"] >= GD["units"], "market_days": n["market_days_with_units"] >= GD["market_days"]}
    n["gate_gd"] = {**gate, "pass": all(gate.values()), "thresholds": GD, "counted_on": "units entering D1 (m_c available, next transaction within 10 minutes)"}
    n["mde_c"] = MDE_Z * D_SD_C * math.sqrt(D_DEFF / n["units_with_next_tx"]) if n["units_with_next_tx"] else None
    return n


def _d_rows(units: list[dict], *, usd: bool = False) -> list[dict]:
    out = []
    for u in units:
        if not u["prints_ok"]:
            continue
        du, _ = dust_units(u, usd=usd)
        for x in du:
            nt = next_tx(u["post"], x["u"])
            if nt is None:
                continue
            out.append({**x, "P": nt["vwap"], "P_last": nt["last"], "size": nt["size"], "md_key": f"{u['market_id']}|{u['day']}", "day": u["day"], "month": u["month"],
                        "liquidity": u["liquidity"]})
    return out


def _d_values(rows: list[dict], key: str = "P") -> np.ndarray:
    return np.array([100.0 * (abs(r[key] - r["m_d"]) - abs(r[key] - r["m_c"])) for r in rows], float)


def d1_stat(rows: list[dict], key: str = "P") -> dict:
    if not rows:
        return {"n": 0, "effect_c": math.nan, "p": 1.0, "testable": False}
    v = _d_values(rows, key)
    cp = c9.cluster_p(v, {"market_day": np.array([r["md_key"] for r in rows], object), "day": np.array([r["day"] for r in rows], object)})
    return {"n": len(rows), "effect_c": float(v.mean()), "p": cp["p"], "testable": cp["testable"], "ways": cp["ways"]}


def d1_analysis(units: list[dict], *, gate_ok: bool, labels: dict, seed: int = c9.PLACEBO_SEEDS["D1_shuffle"], n_draws: int = c9.PLACEBO_DRAWS,
                alpha: float = c9.GATE_P) -> dict:
    rows = _d_rows(units)
    main = d1_stat(rows)
    res: dict = {"test": "D1", "unit": "dust unit (outcome-0 token, market-minute)", "n_units": len(rows), "estimate": main, "floor_c": D1_FLOOR_C, "alpha": alpha}
    if not gate_ok or not rows or not main["testable"]:
        res.update(testable=False, p=1.0, advance=False, verdict=labels.get("d_gate_label") or "not testable")
        return res
    est = main["effect_c"]
    # placebo: next-transaction prices permuted across dust units within each market x day
    rng = np.random.default_rng(seed)
    groups: dict[str, list[int]] = {}
    for i, r in enumerate(rows):
        groups.setdefault(r["md_key"], []).append(i)
    draws = []
    P = np.array([r["P"] for r in rows])
    for _ in range(n_draws):
        Pp = P.copy()
        for idxs in groups.values():
            if len(idxs) > 1:
                Pp[idxs] = P[rng.permutation(idxs)]
        sh = [{**r, "P": float(Pp[i])} for i, r in enumerate(rows)]
        draws.append(d1_stat(sh)["p"])
    plc = c9.placebo_advance_rate(draws, alpha)
    v = _d_values(rows)
    rob: dict = {}
    top = {}
    for way, cl in (("market_day", np.array([r["md_key"] for r in rows], object)), ("day", np.array([r["day"] for r in rows], object))):
        keep = c9.top_k_drop_mask(v, cl)
        sub = [r for r, k in zip(rows, keep, strict=True) if k]
        st = d1_stat(sub)
        top[way] = {"effect_c": st["effect_c"], "p": st["p"], "holds": bool(st["p"] < alpha and st["effect_c"] >= D1_FLOOR_C)}
    rob["top5_drops"] = {**top, "holds": all(x["holds"] for x in top.values())}
    w = np.array([r["size"] for r in rows])
    sw = float((v * w).sum() / w.sum()) if w.sum() > 0 else math.nan
    rob["size_weighted"] = {"effect_c": sw, "holds": bool(np.sign(sw) == np.sign(est))}
    months = {}
    for mo in sorted({r["month"] for r in rows}):
        mv = np.array([x for x, r in zip(v, rows, strict=True) if r["month"] == mo])
        if len(mv) < D_MONTH_MIN_UNITS:
            continue
        months[mo] = {"units": int(len(mv)), "effect_c": float(mv.mean()), "same_sign": bool(np.sign(mv.mean()) == np.sign(est))}
    rob["months"] = {"months": months, "holds": bool(months) and sum(m["same_sign"] for m in months.values()) >= (2.0 / 3.0) * len(months), "unknown": not months}
    rob_ok = all(x["holds"] for x in rob.values())
    advance = bool(main["p"] < alpha and est >= D1_FLOOR_C and plc["holds"] and rob_ok)
    verdict = "advance" if advance else (f"not detected at MDE {labels.get('d_mde_c')}" if main["p"] >= alpha else "no advance (placebo, robustness or floor)")
    last = d1_stat(rows, key="P_last")
    usd_rows = _d_rows(units, usd=True)
    usd = d1_stat(usd_rows)
    md = np.array([abs(r["m_d"] - r["m_c"]) for r in rows])
    res.update(testable=True, p=main["p"], effect=est, advance=advance, verdict=verdict, placebo={"note": "D1 next-transaction shuffle within market x day", **plc, "seed": seed},
               robustness=rob, robustness_holds=rob_ok,
               reported={"last_fill_variant": {"effect_c": last["effect_c"], "p": last["p"]}, "usd_variant": {"effect_c": usd["effect_c"], "p": usd["p"], "n": usd["n"]},
                         "abs_md_minus_mc_c_quantiles": {str(q): float(np.quantile(md, q) * 100.0) for q in (0.1, 0.25, 0.5, 0.75, 0.9)}})
    return res


def d_descriptives(units: list[dict]) -> dict:
    """Dust share by liquidity tercile and price band; share of displayed-mid changes within the hour that coincide with a dust state change."""
    liq = np.array([u["liquidity"] for u in units if math.isfinite(_f(u["liquidity"]))])
    cuts = np.quantile(liq, [1 / 3, 2 / 3]).tolist() if len(liq) >= 3 else None
    by_liq: dict[str, list[int]] = {}
    by_band: dict[str, list[int]] = {}
    mid_changes = dust_changes = 0
    for u in units:
        ms = u["min_size"]
        if not math.isfinite(ms):
            continue
        lt = "unknown" if cuts is None or not math.isfinite(_f(u["liquidity"])) else ("low" if u["liquidity"] < cuts[0] else ("mid" if u["liquidity"] < cuts[1] else "high"))
        prev = None
        for r in u["minutes"]:
            if not minute_ok(r):
                prev = None
                continue
            dust = is_dust(r, ms)
            mdv = (_f(r["best_bid"]) + _f(r["best_ask"])) / 2.0
            band = "<0.10" if mdv < 0.10 else ("0.10-0.90" if mdv <= 0.90 else ">0.90")
            by_liq.setdefault(lt, [0, 0])
            by_band.setdefault(band, [0, 0])
            by_liq[lt][0] += 1
            by_liq[lt][1] += int(dust)
            by_band[band][0] += 1
            by_band[band][1] += int(dust)
            if prev is not None and abs(mdv - prev[0]) > 1e-12:
                mid_changes += 1
                dust_changes += int(dust != prev[1])
            prev = (mdv, dust)
    return {"dust_share_by_liquidity_tercile": {k: v[1] / v[0] for k, v in by_liq.items() if v[0]}, "dust_share_by_price_band": {k: v[1] / v[0] for k, v in by_band.items() if v[0]},
            "mid_changes": mid_changes, "mid_changes_with_dust_state_change_share": dust_changes / mid_changes if mid_changes else None}


# ---- coverage audit and labels ------------------------------------------------------------------------------------------------------------------


def coverage_audit_kd(units: list[dict]) -> dict:
    """(market, day) with >= 1 Data API print in [14:00Z, 15:00Z): PASS iff >= 90% show any pmxt event for the condition id in the span. Unit labels:
    "source unavailable" (a print but no pmxt event), "no fresh book" (neither a print nor a fresh two-sided book), "not processed" (ingress cap / failed day)."""
    pairs = present = 0
    lab = {LABEL_SOURCE_UNAVAILABLE: 0, LABEL_NO_FRESH_BOOK: 0, LABEL_AVAILABLE: 0, LABEL_NOT_PROCESSED: 0}
    for u in units:
        md = u["md"]
        if str(md["books_status"]).startswith("day_ingress_cap") or str(md["prints_status"]).startswith("day_") or md["prints_status"] == "capped":
            lab[LABEL_NOT_PROCESSED] += 1
            continue
        n_pr = int(md.get("n_prints_span") or 0)
        n_ev = int(md.get("n_events_span") or 0)
        if n_pr >= 1:
            pairs += 1
            present += int(n_ev >= 1)
            lab[LABEL_SOURCE_UNAVAILABLE if n_ev == 0 else LABEL_AVAILABLE] += 1
        elif not two_sided_fresh(u["origin"]):
            lab[LABEL_NO_FRESH_BOOK] += 1
        else:
            lab[LABEL_AVAILABLE] += 1
    share = present / pairs if pairs else 0.0
    n_units = len(units)
    avail = 1.0 - (lab[LABEL_SOURCE_UNAVAILABLE] + lab[LABEL_NOT_PROCESSED]) / n_units if n_units else 0.0
    return {"n_pairs": pairs, "n_present": present, "share": share, "pass_threshold": AUDIT_PASS, "pass": bool(pairs and share >= AUDIT_PASS),
            "labels": lab, "source_available_share": avail, "available_min": AVAILABLE_MIN}


def gate_label(gate_pass: bool, audit: dict, disjointness: str, family: str) -> str | None:
    """Label of a not-testable family (design 2.7): disjointness unverified, audit FAIL / low availability -> "not testable (source unavailable)",
    else a gate fail reads "no opportunity"."""
    if disjointness != "verified":
        return "not testable (disjointness unverified)"
    if not audit["pass"]:
        return "not testable (source unavailable)"
    if gate_pass:
        return None
    if audit["source_available_share"] >= AVAILABLE_MIN:
        return {"K": "no opportunity: too few cell fills", "D": "no opportunity: dust is rare, no correction needed"}[family]
    return "not testable (source unavailable)"


# ---- census (q0189, K/D block) ----------------------------------------------------------------------------------------------------------------


def _with_feats(units: list[dict]) -> list[dict]:
    for u in units:
        u["_feat"] = k_features(u)
    return units


def kd_census_doc(root: Path, *, frame_run: str = FRAME_RUN, run_id: str = BOOKS_RUN) -> dict:
    """Counts only (SCREEN; HOLDOUT file and event counts from the seal and the split). No net, contrast, mark-out or next-transaction price."""
    root = Path(root)
    rdir = root / run_id
    seal_p = rdir / SEAL_NAME
    if not seal_p.exists():
        raise c9.Refused(f"{seal_p} not found: the census needs the sealed HOLDOUT (kd-seal) first")
    seal = json.loads(seal_p.read_text())
    sample = read_sample(root / frame_run)
    units = _with_feats(load_units(root, SCREEN, job="census", frame_run=frame_run, run_id=run_id))
    cuts = k_cuts([u["_feat"] for u in units])
    audit = coverage_audit_kd(units)
    disj = seal["drops"]["disjointness"]
    k = k_census_counts(units, cuts)
    d = d_census_counts(units)
    k["label"] = gate_label(k["gate_gk"]["pass"], audit, disj, "K")
    d["label"] = gate_label(d["gate_gd"]["pass"], audit, disj, "D")
    split = {s: {"markets": sum(1 for r in sample if r["split"] == s), "events": len({r["event_key"] for r in sample if r["split"] == s}),
                 "market_days": sum(len(r["days"]) for r in sample if r["split"] == s)} for s in (SCREEN, HOLDOUT)}
    return {"version": "cb9-kd-census-v1", "counts_only": True, "split": split, "holdout_files": seal["n_holdout_files"], "holdout_listing_sha256": seal["listing_sha256"],
            "disjointness": disj, "seal_drops": seal["drops"]["counts"], "audit": audit,
            "k": {**k, "cuts": {"rv_top_tercile": cuts["rv"], "spr_top_tercile": cuts["spr"], "x6_abs_median": cuts["x6_abs"], "n_rv": cuts["n_rv"], "n_spr": cuts["n_spr"],
                                "n_x6": cuts["n_x6"]}},
            "d": d}


def kd_census(args) -> dict:
    """Runner entry for q0189's K/D block (A's ``run_cb9.py census`` stores it under the key ``kd``). ``args.root`` = the creative_batch9 root."""
    root = Path(getattr(args, "root", None) or c9.CB9_DIR)
    c9.refuse_path(root)
    return kd_census_doc(root)


def census_cuts(census: dict) -> dict:
    kd = census.get("kd", census)
    try:
        c = kd["k"]["cuts"]
        return {"rv": float(c["rv_top_tercile"]), "spr": float(c["spr_top_tercile"]), "x6_abs": float(c["x6_abs_median"])}
    except (KeyError, TypeError, ValueError) as exc:
        raise c9.Refused("census has no frozen K cut points (k.cuts); run the census first") from exc


# ---- screen (q0192) and rep (q0197) --------------------------------------------------------------------------------------------------------------


def _labels(census: dict, s0b_label: str | None) -> dict:
    kd = census.get("kd", census)
    return {"k_gate_label": kd["k"].get("label"), "d_gate_label": kd["d"].get("label"), "k_mde_c": kd["k"].get("mde_c"), "d_mde_c": kd["d"].get("mde_c"),
            "s0b_label": s0b_label or "S0b verdict not available at run"}


def screen_kd_doc(root: Path, census: dict, *, s0b_label: str | None = None, frame_run: str = FRAME_RUN, run_id: str = BOOKS_RUN, n_draws: int = c9.PLACEBO_DRAWS) -> dict:
    """K1 and D1 Stage 1 on SCREEN events (never opens holdout/). The census's frozen cut points are used and must equal the recomputed ones."""
    root = Path(root)
    seal = json.loads((root / run_id / SEAL_NAME).read_text()) if (root / run_id / SEAL_NAME).exists() else None
    if seal is None:
        raise c9.Refused("kd-seal has not run")
    units = _with_feats(load_units(root, SCREEN, job="screen", frame_run=frame_run, run_id=run_id))
    cuts = census_cuts(census)
    rec = k_cuts([u["_feat"] for u in units])
    same = all(abs(rec[k] - cuts[k]) <= 1e-12 or (math.isnan(rec[k]) and math.isnan(cuts[k])) for k in ("rv", "spr", "x6_abs"))
    if not same:
        raise c9.Refused(f"SCREEN cut points recomputed {[rec[k] for k in ('rv', 'spr', 'x6_abs')]} differ from the census's frozen ones {cuts}; refusing")
    kd = census.get("kd", census)
    labels = _labels(census, s0b_label)
    k = k1_analysis(units, cuts, gate_ok=kd["k"].get("label") is None, labels=labels, n_draws=n_draws)
    d = d1_analysis(units, gate_ok=kd["d"].get("label") is None, labels=labels, n_draws=n_draws)
    return {"version": "cb9-kd-screen-v1", "stage": 1, "split": SCREEN, "cuts": cuts, "K1": k, "D1": d, "descriptives_D": d_descriptives(units),
            "holdout_listing_sha256": seal["listing_sha256"], "disjointness": seal["drops"]["disjointness"]}


def stage1_recorded(results_path: Path, trials_path: Path) -> dict:
    """The Stage-1 result file and a trials line carrying its sha256 with an advanced K1 or D1. Returns {"K1": bool, "D1": bool} of advanced tests."""
    rp = Path(results_path)
    if not rp.exists():
        raise c9.Refused(f"{rp} not found: rep-kd runs only after the Stage-1 screen")
    doc = json.loads(rp.read_text())
    sha = doc.get("results_sha256")
    adv = {t: bool((doc.get(t) or {}).get("advance")) for t in ("K1", "D1")}
    if not any(adv.values()):
        raise c9.Refused("neither K1 nor D1 advanced: HOLDOUT stays sealed")
    hits = set()
    tp = Path(trials_path)
    if tp.exists():
        for line in tp.read_text().splitlines():
            try:
                j = json.loads(line)
            except ValueError:
                continue
            if j.get("kind") == "cb9_test" and j.get("results_sha256") == sha and j.get("advance") is True:
                hits.add(j.get("hypothesis"))
    for t, a in adv.items():
        if a and t not in hits:
            raise c9.Refused(f"{t} advanced in {rp.name} but no trials line records that result (sha {sha}); refusing to open HOLDOUT")
    return adv


def rep_kd_doc(root: Path, census: dict, advanced: dict, *, stage2_k: int, seals_dir: Path | None = None, s0b_label: str | None = None, frame_run: str = FRAME_RUN,
               run_id: str = BOOKS_RUN, n_draws: int = c9.PLACEBO_DRAWS) -> dict:
    """K1-rep / D1-rep on the sealed HOLDOUT events with the SCREEN cut points, only for advanced tests; judged at one-sided alpha 0.05 / k (Holm's first
    step: early finishers), in the Stage-1 direction, with the same floors and binding checks."""
    if not isinstance(stage2_k, int) or stage2_k < 1:
        raise c9.Refused("--stage2-k (the number of CB9 tests reaching Stage 2) is required")
    root = Path(root)
    seal = verify_holdout_seal(root / run_id, seals_dir)
    alpha = c9.STAGE2_ALPHA / stage2_k
    cuts = census_cuts(census)
    units = _with_feats(load_units(root, HOLDOUT, job="rep", frame_run=frame_run, run_id=run_id))
    labels = _labels(census, s0b_label)
    audit = coverage_audit_kd(units)
    disj = seal["drops"]["disjointness"]
    out = {"version": "cb9-kd-rep-v1", "stage": 2, "split": HOLDOUT, "alpha": alpha, "stage2_k": stage2_k, "cuts_from": "SCREEN (census)", "audit": audit,
           "holdout_listing_sha256": seal["listing_sha256"]}
    # Stage 2 testability: disjointness and the coverage audit on HOLDOUT, then >= 100 units and >= 30 clusters per way (cluster_p). The SCREEN census gates
    # GK / GD are not re-imposed on HOLDOUT (the design declares them for SCREEN only); their HOLDOUT counts are reported.
    if advanced.get("K1"):
        g = k_census_counts([{**u, "post": _ArrayCounts(u["post"]) if u["post"] is not None else None} for u in units], cuts)
        lab = gate_label(True, audit, disj, "K")
        out["K1_rep"] = {**k1_analysis(units, cuts, gate_ok=lab is None, labels={**labels, "k_gate_label": lab}, alpha=alpha, n_draws=n_draws), "holdout_gk_counts_reported": g["gate_gk"]}
    if advanced.get("D1"):
        g = d_census_counts([{**u, "post": _ArrayCounts(u["post"]) if u["post"] is not None else None} for u in units])
        lab = gate_label(True, audit, disj, "D")
        out["D1_rep"] = {**d1_analysis(units, gate_ok=lab is None, labels={**labels, "d_gate_label": lab}, alpha=alpha, n_draws=n_draws), "holdout_gd_counts_reported": g["gate_gd"]}
    return out


class _ArrayCounts(CountOnlyPosts):
    """The count interface over already-loaded arrays (rep-kd recomputes the gates on HOLDOUT)."""

    def __init__(self, arrays: dict[str, np.ndarray]) -> None:  # noqa: D107
        self._a = arrays


# ---- runner interface (A's backend/scripts/run_cb9.py) ------------------------------------------------------------------------------------------


REFUSED_EXIT, TEMPFAIL_EXIT, DISK_BUDGET_EXIT = cm.REFUSED_EXIT, cm.TEMPFAIL_EXIT, cm.DISK_BUDGET_EXIT


def _emit(obj: dict) -> None:
    print(json.dumps(obj, default=str, sort_keys=True))


def _guarded(fn):
    def wrapper(a) -> int:
        try:
            code, payload = fn(a)
        except c9.Refused as exc:
            _emit({"refused": str(exc)})
            return REFUSED_EXIT
        except c9.NotNow as exc:
            _emit({"tempfail": str(exc)})
            return TEMPFAIL_EXIT
        except (h5_seal.SealError, FileNotFoundError) as exc:
            _emit({"refused": str(exc)})
            return REFUSED_EXIT
        except Exception as exc:
            _emit({"error": f"{type(exc).__name__}: {exc}"[:300]})
            return 1
        _emit(payload)
        return code

    wrapper.__name__ = getattr(fn, "__name__", "handler")
    return wrapper


def _result(m: dict) -> tuple[int, dict]:
    if m.get("status") == cm.DISK_BUDGET_TOKEN:
        return DISK_BUDGET_EXIT, {"status": cm.DISK_BUDGET_TOKEN, "stopped": m.get("stopped"), "counts": m.get("counts")}
    return 0, {"status": m.get("status") or ("in_progress" if m.get("stopped") else None), "stopped": m.get("stopped"), "complete": m.get("complete"),
               "counts": m.get("counts"), "transient": m.get("transient"), "requests": m.get("requests")}


def _declared_args(a, checks: dict) -> None:
    bad = [f"{k}={got!r} (declared {want!r})" for k, (got, want) in checks.items() if got != want]
    if bad:
        raise c9.Refused(f"arguments differ from the declaration: {bad}")


def _rules(a) -> tuple[str, str]:
    return c9.verify_rules("kd", Path(a.rules) if a.rules else None, require_committed=not a.allow_uncommitted_rules)


def _net(a) -> dict:
    standalone = bool(a.standalone)
    return dict(data_dumps=Path(a.data_dumps) if a.data_dumps else cm.DATA_DUMPS, data_dumps_cap_gb=a.data_dumps_cap_gb,
                live_check=None if standalone else hb.live_pass_or_lock, snapshot_root=None if standalone else Path(a.snapshot_root or c4.SNAPSHOT_ROOT),
                budget_min=a.budget_min)


def _root(a) -> Path:
    root = Path(a.root) if a.root else c9.CB9_DIR
    c9.refuse_path(root)
    return root


@_guarded
def cmd_kd_frame(a):
    _declared_args(a, {"disk_cap_gb": (a.disk_cap_gb, FRAME_OUTPUT_CAP_GB)})
    sha, _fp = _rules(a)
    m = kd_frame(_root(a), hb.httpx_transport(), rules_sha=sha, exclusion_keys_path=Path(a.exclusion_keys) if a.exclusion_keys else None, rps=min(a.rps, MAX_RPS_FRAME),
                 disk_cap=int(a.disk_cap_gb * 1024**3), **_net(a))
    return _result(m)


@_guarded
def cmd_kd_books(a):
    _declared_args(a, {"disk_cap_gb": (a.disk_cap_gb, BOOKS_OUTPUT_CAP_GB), "ingress_cap_gb": (a.ingress_cap_gb, INGRESS_CAP_GB)})
    sha, fp = _rules(a)
    if not fp:
        raise c9.Refused("the kd rules file pins no wallet_key_fingerprint (design 1.4: q0186 hashes proxyWallet through the strict loader)")
    key = cm.load_wallet_key_strict(Path(a.wallet_key_path) if a.wallet_key_path else None, fp)
    m = kd_books(_root(a), hb.httpx_transport(), rules_sha=sha, key=key, fp=fp, fetch=hs.httpx_range_fetch(), size_fn=hs.httpx_size, ingress_cap_gb=a.ingress_cap_gb,
                 rps=min(a.rps, MAX_RPS_BOOKS), disk_cap=int(a.disk_cap_gb * 1024**3), **_net(a))
    return _result(m)


@_guarded
def cmd_kd_seal(a):
    from . import cb1_history  # noqa: PLC0415

    sha, _fp = _rules(a)
    out = kd_seal(_root(a), rules_sha=sha, transport=hb.httpx_transport(), seals_dir=Path(a.seals_dir) if a.seals_dir else None, rps=min(a.rps, MAX_RPS_SEAL),
                  live_check=None if a.standalone else hb.live_pass_or_lock, is_committed=None if a.allow_uncommitted_rules else cb1_history.spec_committed)
    return 0, out


def _s0b_label(path: str | None) -> str | None:
    p = Path(path) if path else c9.CB9_DIR / "results_S0.json"
    if not p.exists():
        return None
    try:
        doc = json.loads(p.read_text())
    except ValueError:
        return None
    b = (doc.get("strata") or {}).get("b") or doc.get("s0b") or {}
    v = b.get("verdict") if isinstance(b, dict) else None
    return f"S0b: {v}" if v else None


def _write_results(path: Path, doc: dict) -> str:
    sha = cm.sha_obj(doc)
    cm.write_json_atomic(path, {**doc, "results_sha256": sha})
    return sha


@_guarded
def cmd_screen_kd(a):
    c9.require_freeze(Path(a.freeze_spec) if a.freeze_spec else None, require_committed=not a.allow_uncommitted_rules)
    sha, _fp = _rules(a)
    root = _root(a)
    census = json.loads(Path(a.census or (root / "census.json")).read_text())
    doc = screen_kd_doc(root, census, s0b_label=_s0b_label(a.s0_results))
    doc["rules_sha256"] = sha
    out = Path(a.out) if a.out else root / RESULTS_NAME
    rsha = _write_results(out, doc)
    tp = Path(a.trials_path) if a.trials_path else None
    for fam, t in (("K", "K1"), ("D", "D1")):
        r = doc[t]
        c9.log_test(fam, t, {"p": r.get("p", 1.0), "advance": r.get("advance"), "testable": r.get("testable"), "effect": r.get("effect"), "n": r.get("n_units"),
                             "verdict": r.get("verdict")}, trials_path=tp, results_sha256=rsha,
                    placebo={"note": r["placebo"]["note"], "advance_rate": r["placebo"]["advance_rate"], "n_draws": r["placebo"]["n_draws"]} if r.get("placebo") else None)
    return 0, {"status": "screen_kd_complete", "results": str(out), "results_sha256": rsha, "K1": {k: doc["K1"].get(k) for k in ("p", "advance", "verdict")},
               "D1": {k: doc["D1"].get(k) for k in ("p", "advance", "verdict")}}


@_guarded
def cmd_rep_kd(a):
    from . import provenance  # noqa: PLC0415

    c9.require_freeze(Path(a.freeze_spec) if a.freeze_spec else None, require_committed=not a.allow_uncommitted_rules)
    sha, _fp = _rules(a)
    root = _root(a)
    tp = Path(a.trials_path) if a.trials_path else provenance.TRIALS_PATH
    adv = stage1_recorded(Path(a.stage1_results) if a.stage1_results else root / RESULTS_NAME, tp)
    census = json.loads(Path(a.census or (root / "census.json")).read_text())
    doc = rep_kd_doc(root, census, adv, stage2_k=a.stage2_k, seals_dir=Path(a.seals_dir) if a.seals_dir else None, s0b_label=_s0b_label(a.s0_results))
    doc["rules_sha256"] = sha
    out = Path(a.out) if a.out else root / REP_RESULTS_NAME
    rsha = _write_results(out, doc)
    for fam, t, key in (("K", "K1", "K1_rep"), ("D", "D1", "D1_rep")):
        if key in doc:
            r = doc[key]
            c9.log_test(fam, f"{t}-rep", {"p": r.get("p", 1.0), "advance": r.get("advance"), "testable": r.get("testable"), "effect": r.get("effect"),
                                          "n": r.get("n_units"), "verdict": r.get("verdict")}, replication=True, trials_path=tp, results_sha256=rsha,
                        placebo={"note": r["placebo"]["note"], "advance_rate": r["placebo"]["advance_rate"], "n_draws": r["placebo"]["n_draws"]} if r.get("placebo") else None)
    return 0, {"status": "rep_kd_complete", "results": str(out), "results_sha256": rsha, "tests": [k for k in ("K1_rep", "D1_rep") if k in doc]}


def add_subparsers(subparsers) -> None:
    """Register kd-frame, kd-books, kd-seal, screen-kd and rep-kd on A's ``run_cb9.py`` subparsers. Each sets ``fn`` (``fn(args) -> exit code``):
    0 ok / transient pause / declared end state; 1 error; 2 refusal (rules hash, key, run id, refused root, T_seal, declared arguments changed, holdout,
    freeze); 4 disk budget; 75 data-dumps headroom or not finished yet."""

    def common(q, *, rps: float) -> None:
        q.add_argument("--root", default=None, help="creative_batch9 root (default data-dumps/research_lab/creative_batch9)")
        q.add_argument("--rules", default=None, help="default docs/research_lab/seals/cb9_kd_rules.json")
        q.add_argument("--rps", type=float, default=rps)
        q.add_argument("--standalone", action="store_true", help="no collector yield / health check (tests, off-host)")
        q.add_argument("--allow-uncommitted-rules", action="store_true")

    def net(q, *, disk_cap: float) -> None:
        q.add_argument("--data-dumps", default=None)
        q.add_argument("--snapshot-root", default=None)
        q.add_argument("--disk-cap-gb", type=float, default=disk_cap)
        q.add_argument("--data-dumps-cap-gb", type=float, default=DATA_DUMPS_CAP_GB)
        q.add_argument("--budget-min", type=float, default=None)

    q = subparsers.add_parser("kd-frame", help="q0185: K/D Gamma frame, key drops, seeded sample, event split")
    common(q, rps=MAX_RPS_FRAME)
    net(q, disk_cap=FRAME_OUTPUT_CAP_GB)
    q.add_argument("--exclusion-keys", default=None, help="default creative_batch9/exclusion_keys.csv.gz (q0182)")
    q.set_defaults(fn=cmd_kd_frame)

    q = subparsers.add_parser("kd-books", help="q0186: pmxt hour 14Z states, minute states, ltp events; Data API prints [t-6h, t+7h]")
    common(q, rps=MAX_RPS_BOOKS)
    net(q, disk_cap=BOOKS_OUTPUT_CAP_GB)
    q.add_argument("--wallet-key-path", default=None, help="default ~/.arepo/wallet_hash_key (or AREPO_WALLET_HASH_KEY_PATH); never created")
    q.add_argument("--ingress-cap-gb", type=float, default=INGRESS_CAP_GB)
    q.set_defaults(fn=cmd_kd_books)

    q = subparsers.add_parser("kd-seal", help="q0187: HOLDOUT listing sha256, seal-time drops, seal copy")
    common(q, rps=MAX_RPS_SEAL)
    q.add_argument("--seals-dir", default=None)
    q.set_defaults(fn=cmd_kd_seal)

    for name, fn, helptext in (("screen-kd", cmd_screen_kd, "q0192: K1, D1 Stage 1 on SCREEN events"), ("rep-kd", cmd_rep_kd, "q0197: K1-rep / D1-rep on sealed HOLDOUT events")):
        q = subparsers.add_parser(name, help=helptext)
        common(q, rps=1.0)
        q.add_argument("--census", default=None, help="census.json (default <root>/census.json; the K/D block under 'kd')")
        q.add_argument("--out", default=None)
        q.add_argument("--trials-path", default=None)
        q.add_argument("--freeze-spec", default=None)
        q.add_argument("--s0-results", default=None, help="results_S0.json for the S0b label (default <CB9>/results_S0.json if present)")
        if name == "rep-kd":
            q.add_argument("--stage2-k", type=int, required=True, help="number of CB9 tests reaching Stage 2 (Holm k)")
            q.add_argument("--stage1-results", default=None)
            q.add_argument("--seals-dir", default=None)
        q.set_defaults(fn=fn)


def rule_funcs() -> tuple:
    return (declared, window_days, origin_epoch, _num, kd_row, overlap_days, frame_reason, market_days, frame_walk_days, _walk_window, walk_frame, kd_sample,
            assemble_kd, read_sample, kd_frame, read_events_kd, _fee, kd_state, _tick_of, day_books, market_day_prints, day_order, _require_frame, kd_books,
            finalize_books, kd_seal, verify_holdout_seal, _guard_split, _guard_post, dropped_ids, _print_arrays, CountOnlyPosts, load_units, two_sided_fresh,
            x6_feature, rv_feature, k_features, k_cuts, in_cell, skew_dir, quote_prices, level_depth, _pr, _fill, mark_value, _origin_book, quote_result, _quote_result,
            k_census_counts, _single, contrast, route_gate, _k_rows, _k_arrays, k1_stat, k1_analysis, next_tx, minute_ok, is_dust, dust_units, d_census_counts, _d_rows,
            _d_values, d1_stat, d1_analysis, coverage_audit_kd, gate_label, kd_census_doc, census_cuts, screen_kd_doc, stage1_recorded, rep_kd_doc,
            fl.flow_sample, fl.per_event_cap, fl.event_split, fl.event_key, bk._levels, bk._ms, bk._check_clock, bk.seal_copy_ids_audited, bk.ingress_used,
            bk.ingress_add, cm.windowed_prints, cm._parse_print, mk.quote_fills, c7.is_weather, c7.key_types_matched, hb._rank, hb.allocate_weighted,
            h5_seal.listing_sha256, h5_seal.list_files)

