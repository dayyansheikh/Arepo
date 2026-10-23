# ruff: noqa: E501
"""CB8-B data side, part 1 (docs/research_lab/CREATIVE_BATCH_8.md CB8-B, CB8-F, 5.1): the frozen B rules (market regexes incl. the strike clause,
asset list, windows, thresholds, alternating-week split, fee rule, latency rule, day-unit tail gate with its Clopper-Pearson bound), the rules file
``seals/cb8_rules.json``, the q0161 smoke, the q0164 exclusion keys, and the q0165 frame + Binance 1m archive fetch.

Exploratory historical data (rows before 2026-08-10); NOT bound to T_seal. Data only: no statistic is computed from an outcome. Gamma outcome
prices and the Binance settlement candles go to ``*_guarded.csv.gz`` files only; the feature files hold candles with ``open_time < t_end(d)`` and
the strike. No function compares consecutive strikes. The books side (pmxt, prints, coverage audit, HOLDOUT seal) is ``cb8_books``.
"""

from __future__ import annotations

import csv
import hashlib
import inspect
import io
import json
import math
import re
import shutil
import time
import zipfile
from collections.abc import Callable, Iterator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from . import cb4_data as c4
from . import cb6_tail as c6
from . import cb7_common as c7
from . import cb8_common as cm
from . import economics as econ
from . import h5_seal
from . import history_backfill as hb

RULES_VERSION = "cb8-updown-rules-v3"  # v3: B only, series key waived (CREATIVE_BATCH_8.md 1.3 "Amendment 2026-10-23", reviews/CB8B_SERIES_KEY_RULING_2026-10-23.md); new run dirs updown_frame_b / updown_b. v2: freeze-check fixes (hashed dependencies, split HOLDOUT klines, book_unavailable, ...); v1 file kept, superseded
SMOKE_VERSION = "cb8-smoke-v1"
RUN_FRAME = "updown_frame_b"  # v3: new run directory (the v2 run dir updown_frame holds the empty q0165 frame and is never opened, reused or moved)
RUN_FRAME_V2 = "updown_frame"  # q0165 (v2), recorded "frame empty (series overlap); operational, nothing counted"; never touched
RUN_KEYS = "exclusion_run"
RULES_FILE = cm.SEALS_DIR / "cb8_rules_v3.json"
RULES_FILE_V2 = cm.SEALS_DIR / "cb8_rules_v2.json"  # consumed by q0161 / q0164c / q0165 / q0166; never rewritten
RULES_SHA_V2 = "33decb528bbafd46336296be57c91b76e6aaa0c69d7d3eecf92eaa83c4f12a6d"
SMOKE_ACCEPT_SHAS = (RULES_SHA_V2,)  # the q0161 smoke (criteria b, c: Binance checksum, pmxt HEAD) was made under v2; the amendment changes neither source test
B_KEY_TYPES = ("event", "neg_risk_market")  # v3: the series key is waived for B (c7.KEY_TYPES also holds "series"); market-id, event-id and neg-risk keys stay
RULES_FILE_V1 = cm.SEALS_DIR / "cb8_rules.json"  # superseded before any B job ran; never rewritten
SMOKE_DEFAULT = cm.CB8_DIR / "smoke.json"
EXCLUSION_KEYS_DEFAULT = cm.CB8_DIR / "exclusion_keys.csv.gz"
FRAME_COMPLETE = "updown_frame_complete"
KEYS_COMPLETE = "exclusion_keys_complete"
REQUIRED_EXTRA_PINS = ("c1_legs", "cb5_listings")  # design 1.3: C1 Polymarket legs and every CB5 sample listing; q0164 cannot be re-run, so it refuses without them
UNVERIFIED = "disjointness_unverified"
SOURCE_UNVERIFIED = "source_unverified"
HOLDOUT_SUBDIR = "holdout"  # HOLDOUT-day kline features and strikes of the frame run; sealed by cb8_books.seal_holdout

# ---- the frozen B population rules ----------------------------------------------------------------------------------------------------

B_FIRST, B_END = "2026-04-13", "2026-08-10"  # days d in [B_FIRST, B_END) minus the pmxt gap; t_end(d) = d 16:00:00Z (12:00 EDT)
STRIKE_FIRST = "2026-04-12"  # the strike of the first B day is the settlement close of this day
GAP = ("2026-06-12", "2026-06-18")  # pmxt gap, absent days [06-12, 06-18)
T_END_HOUR = 16
ASSETS = {"Bitcoin": ("BTC", "spot"), "Ethereum": ("ETH", "spot"), "Solana": ("SOL", "spot"), "XRP": ("XRP", "spot"), "Dogecoin": ("DOGE", "spot"),
          "HYPE": ("HYPE", "um"), "BNB": ("BNB", "spot")}
QUESTION_RE = r"^(Bitcoin|Ethereum|Solana|XRP|Dogecoin|HYPE|BNB) Up or Down on [A-Z][a-z]+ \d{1,2}\??$"
FLAG_RES = {"binance": r"(?i)binance", "candle_1m": r"(?i)1[- ]?minute|1m\b", "noon_et": r"12:00\s*(PM)?\s*ET", "tie_50_50": r"50-50|50/50"}
UP_RE = r"""resolve to "Up" if the "Close" price for the Binance 1 minute candle for ([A-Z]+/USDT) ([A-Z][a-z]{2} \d{1,2} '\d{2}) 12:00 in the ET timezone \(noon\) is lower than the final "Close" price for the ([A-Z][a-z]{2} \d{1,2} '\d{2}) 12:00 ET candle"""
DOWN_RE = r"""resolve to "Down" if the "Close" price for the Binance 1 minute candle for ([A-Z]+/USDT) ([A-Z][a-z]{2} \d{1,2} '\d{2}) 12:00 in the ET timezone \(noon\) is higher than the final "Close" price for the ([A-Z][a-z]{2} \d{1,2} '\d{2}) 12:00 ET candle"""
SOURCE_SPOT_RE = r"^https?://(?:www\.)?binance\.com/(?:[A-Za-z]{2}(?:-[A-Za-z]{2})?/)?trade/([A-Z0-9]+)_USDT/?(?:\?.*)?$"
SOURCE_UM_RE = r"^https?://(?:www\.)?binance\.com/(?:[A-Za-z]{2}(?:-[A-Za-z]{2})?/)?futures/([A-Z0-9]+)USDT/?(?:\?.*)?$"
OUTCOME_LABELS = ("Up", "Down")
GAMMA_WINDOW = ("15:59:00", "16:01:00")
SEED_SPLIT = "arepo-cb8-updown-split"
WEEKS = (16, 32)  # ISO weeks of the B days; pairs (16,17) .. (30,31); week 32 by its own coin
# features and checkpoints
CHECKPOINTS_S = (300, 120, 60)  # units; t = t_end - s
REPORT_CHECKPOINT_S = 600  # reported only
LATENCY_S = 10
CANDLE_USABLE_S = 65  # a 1m candle opening at o is usable at t iff o + 65 s <= t
N_SIGMA = 60
SIGMA_MIN_PRESENT = 55
Z_MIN = 3.0
FRESH_S = 120
BUY_CAP = 0.99
MIN_SHARES = 5.0
PRE_MIN = 75  # minutes of pre-t_end candles kept per day (60 for sigma + the usable lag + slack)
TAIL_CONF = 0.99
EDGE_FLOOR = 0.005
SOURCE_DISAGREE_MAX = 0.02
MAX_UNVERIFIED_KEY_SHARE = 0.02
FRAME_OUTPUT_CAP_GB = 0.02
KEYS_OUTPUT_CAP_GB = 0.01
BINANCE_RPS = 2.0
BINANCE_BASE = "https://data.binance.vision/data"
MONTHS = ("2026-04", "2026-05", "2026-06", "2026-07", "2026-08")
SMOKE_SEED_POOL = "arepo-cb8-smoke-pool"
SMOKE_SEED_PMXT = "arepo-cb8-smoke-pmxt"
SMOKE_N = 20
SMOKE_CANDIDATES = 200
SMOKE_MIN_VOLUME = 50000.0
SMOKE_MIN_LIFE_DAYS = 10
SMOKE_END_FROM, SMOKE_END_TO = "2026-05-01T00:00:00Z", "2026-10-01T00:00:00Z"
SMOKE_DAY_PAGES = 10
SMOKE_MIN_NONEMPTY = 14
SMOKE_MAX_CAPPED = 2
SMOKE_DEEP_OFFSET = 4000
SMOKE_BINANCE = (("BTCUSDT", "spot", "2026-03"), ("HYPEUSDT", "um", "2026-03"))
SMOKE_PMXT_HOURS = 3
PRINT_LIMIT = 1000


# ---- days, weeks, split, clocks ----------------------------------------------------------------------------------------------------------


def d_of(s: str) -> date:
    return date.fromisoformat(s)


def t_end(day: str) -> float:
    """Epoch of the settlement candle's open: 12:00 America/New_York = 16:00:00Z on every B day (all in EDT)."""
    return datetime(*d_of(day).timetuple()[:3], T_END_HOUR, tzinfo=UTC).timestamp()


def all_days(first: str = STRIKE_FIRST, end: str = B_END) -> list[str]:
    a, b = d_of(first), d_of(end)
    return [(a + timedelta(days=i)).isoformat() for i in range((b - a).days)]


def b_days() -> list[str]:
    """B days: [2026-04-13, 2026-08-10) minus the pmxt gap [06-12, 06-18)."""
    return [d for d in all_days(B_FIRST, B_END) if not (GAP[0] <= d < GAP[1])]


def week_split(seed: str = SEED_SPLIT) -> dict[int, str]:
    """ISO week -> ``screen`` / ``holdout``. Weeks (16,17), (18,19) .. (30,31) are pairs: in each pair one week is SCREEN and one HOLDOUT by a
    seeded coin on the pair's first week; week 32 has its own coin (0 = SCREEN)."""
    out: dict[int, str] = {}
    for w in range(WEEKS[0], WEEKS[1], 2):
        coin = int(hashlib.sha256(f"{seed}|pair|{w}".encode()).hexdigest(), 16) % 2
        out[w], out[w + 1] = ("screen", "holdout") if coin == 0 else ("holdout", "screen")
    if WEEKS[1] % 2 == 0:
        out[WEEKS[1]] = "screen" if int(hashlib.sha256(f"{seed}|single|{WEEKS[1]}".encode()).hexdigest(), 16) % 2 == 0 else "holdout"
    return out


def day_split(day: str, seed: str = SEED_SPLIT) -> str:
    return week_split(seed)[d_of(day).isocalendar()[1]]


# ---- market parse ------------------------------------------------------------------------------------------------------------------------------


def _pd(s: str) -> date:
    return datetime.strptime(s.replace("'", ""), "%b %d %y").date()


def parse_updown(question: str, description: str, resolution_source: str, day: str) -> dict:
    """Frozen population rules 2-4 and 3a for the market that ends on ``day``. ``{"ok": True, asset, symbol, venue}`` or ``{"ok": False,
    "reason": ...}``. The strike clause must be mirrored (same symbol, strike date, settlement date) with strike date = day - 1 and settlement date =
    day. ``resolutionSource`` must parse to a Binance spot pair (``/trade/<SYM>_USDT``) or a USD-M future (``/futures/<SYM>USDT``) matching the
    asset map and the asset's archive venue (HYPE: futures, the others spot)."""
    m = re.match(QUESTION_RE, str(question or ""))
    if not m:
        return {"ok": False, "reason": "question_pattern"}
    asset = m.group(1)
    sym, want_venue = ASSETS[asset]
    text = str(description or "")
    if not all(re.search(p, text) for p in FLAG_RES.values()):
        return {"ok": False, "reason": "description_flags"}
    u, w = re.search(UP_RE, text), re.search(DOWN_RE, text)
    if not (u and w):
        return {"ok": False, "reason": "strike_clause_missing"}
    if u.groups() != w.groups():
        return {"ok": False, "reason": "strike_clause_not_mirrored"}
    try:
        ok_dates = _pd(u.group(2)) == d_of(day) - timedelta(days=1) and _pd(u.group(3)) == d_of(day)
    except ValueError:
        ok_dates = False
    if not ok_dates:
        return {"ok": False, "reason": "strike_dates"}
    if u.group(1) != f"{sym}/USDT":
        return {"ok": False, "reason": "strike_symbol"}
    src = str(resolution_source or "")
    ms, mu = re.match(SOURCE_SPOT_RE, src), re.match(SOURCE_UM_RE, src)
    venue, ssym = ("spot", ms.group(1)) if ms else (("um", mu.group(1)) if mu else (None, None))
    if venue is None:
        return {"ok": False, "reason": "source_parse"}
    if ssym != sym:
        return {"ok": False, "reason": "source_symbol"}
    if venue != want_venue:
        return {"ok": False, "reason": "source_venue"}
    return {"ok": True, "asset": asset, "symbol": sym, "venue": venue}


# ---- Binance klines, features -----------------------------------------------------------------------------------------------------------


def archive_name(symbol: str, yyyymm: str) -> str:
    return f"{symbol}USDT-1m-{yyyymm}.zip"


def archive_url(symbol: str, venue: str, yyyymm: str) -> str:
    """Keyless data.binance.vision monthly 1m archive: spot ``data/spot/monthly/klines``; USD-M futures ``data/futures/um/monthly/klines``."""
    base = "spot" if venue == "spot" else "futures/um"
    return f"{BINANCE_BASE}/{base}/monthly/klines/{symbol}USDT/1m/{archive_name(symbol, yyyymm)}"


def parse_checksum(text: str) -> str | None:
    """The sha256 in a ``.CHECKSUM`` file (``<hex>  <name>``)."""
    for tok in str(text or "").split():
        if re.fullmatch(r"[0-9a-fA-F]{64}", tok):
            return tok.lower()
    return None


def verify_zip(zip_bytes: bytes, checksum_text: str) -> str:
    """Return the sha256 of the archive; raise :class:`cm.Refused` unless it equals the published checksum."""
    want = parse_checksum(checksum_text)
    got = hashlib.sha256(zip_bytes).hexdigest()
    if want is None or got != want:
        raise cm.Refused(f"archive sha256 {got[:12]} != published checksum {str(want)[:12]}")
    return got


def kline_rows(zip_bytes: bytes) -> Iterator[tuple[int, float]]:
    """``(open_time_ms, close)`` of every row of the single CSV in a monthly archive, streamed. Spot archives from 2025 use microsecond
    timestamps; a value above 1e14 is divided by 1000. A header row and malformed rows are skipped."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        names = [n for n in z.namelist() if n.endswith(".csv")]
        if len(names) != 1:
            raise cm.Refused("archive does not hold exactly one csv")
        with z.open(names[0]) as fh:
            for line in io.TextIOWrapper(fh, encoding="utf-8"):
                f = line.strip().split(",")
                if len(f) < 5:
                    continue
                try:
                    o = int(f[0])
                    c = float(f[4])
                except ValueError:
                    continue
                yield (o // 1000 if o > 10**14 else o), c


def extract_month(rows: Iterator[tuple[int, float]], days: list[str]) -> dict:
    """Per day in ``days``: the candles with ``t_end - PRE_MIN min <= open < t_end`` (``pre``, features) and the candle opening at ``t_end``
    (``settle``, guarded). Everything else in the archive is dropped."""
    want = set(days)
    pre, settle = [], []
    n = 0
    first = last = None
    for o, c in rows:
        n += 1
        first = o if first is None else min(first, o)
        last = o if last is None else max(last, o)
        day = datetime.fromtimestamp(o / 1000, UTC).date().isoformat()
        if day not in want:
            continue
        te = int(t_end(day) * 1000)
        if te - PRE_MIN * 60000 <= o < te:
            pre.append([day, o, c])
        elif o == te:
            settle.append([day, o, c])
    pre.sort()
    settle.sort()
    return {"pre": pre, "settle": settle, "n_rows": n, "first_ms": first, "last_ms": last}


def candle_usable(open_ms: int, t_ms: int) -> bool:
    return open_ms + CANDLE_USABLE_S * 1000 <= t_ms


def min_present(n_sigma: int = N_SIGMA) -> int:
    return math.ceil(n_sigma * SIGMA_MIN_PRESENT / N_SIGMA)


def z_features(candles: list[tuple[int, float]], strike: float, t_ms: int, t_end_ms: int, n_sigma: int = N_SIGMA) -> dict | None:
    """``z_t = ln(S_t/K_d) / (sigma_t * sqrt(m))`` from candles ``(open_ms, close)`` with ``open < t_end``. ``S_t`` is the close of the latest candle usable
    at ``t``. ``sigma_t`` is the sample SD of the 1m log returns of the ``n_sigma`` candles ending at that candle (a return needs the previous minute's
    candle; at least ``min_present`` returns, else ``None``). ``m = (t_end - open of the latest usable candle) / 60 s``. ``None`` if unavailable."""
    usable = [(o, c) for o, c in candles if candle_usable(o, t_ms) and o < t_end_ms]
    if not usable or not (strike > 0):
        return None
    j_open, s_t = max(usable)
    close_of = dict(usable)
    rets = []
    for k in range(n_sigma):
        o = j_open - k * 60000
        p = close_of.get(o - 60000)
        c = close_of.get(o)
        if p is not None and c is not None and p > 0 and c > 0:
            rets.append(math.log(c / p))
    if len(rets) < min_present(n_sigma):
        return None
    mean = sum(rets) / len(rets)
    sd = math.sqrt(sum((x - mean) ** 2 for x in rets) / (len(rets) - 1))
    m = (t_end_ms - j_open) / 60000.0
    if not (sd > 0 and m > 0 and s_t > 0):
        return None
    z = math.log(s_t / strike) / (sd * math.sqrt(m))
    return {"z": z, "sigma": sd, "m": m, "s_t": s_t, "n_returns": len(rets), "side": "up" if z > 0 else ("down" if z < 0 else None)}


# ---- units, fee, latency, tail gate ---------------------------------------------------------------------------------------------------


def eligible_unit(z: float | None, fresh: bool, crossed: bool) -> bool:
    """Eligible iff features are available, |z| >= 3 and the favoured token's book is fresh and not crossed."""
    return z is not None and abs(z) >= Z_MIN and bool(fresh) and not crossed


def traded_unit(ask: float | None, ask_size: float | None) -> bool:
    """Traded iff the best ask is <= 0.99 and the size at it is >= 5 shares."""
    return ask is not None and ask_size is not None and ask <= BUY_CAP and ask_size >= MIN_SHARES


def fee_rate(recorded_bps: float | None) -> float:
    """r = max(recorded fee_rate_bps / 1e4, the docs crypto rate 0.07): no fee era makes B cheaper than the docs rate."""
    rec = 0.0 if recorded_bps is None or not math.isfinite(float(recorded_bps)) else float(recorded_bps) / 1e4
    return max(rec, econ.DOCS_CATEGORY_RATE["crypto"])


def taker_fee_per_share(price: float, rate: float) -> float:
    return rate * price * (1.0 - price)


def unit_net(y_fav: float, ask: float, rate: float) -> float:
    """Net per share bought at the recorded ask and held to settlement: ``Y_fav - a - f(a)``. A 50-50 resolution pays 0.5."""
    return y_fav - ask - taker_fee_per_share(ask, rate)


def latency_fill(ask_t: float | None, ladder_t10: list, min_shares: float = MIN_SHARES, cap: float = BUY_CAP) -> float | None:
    """Latency robustness: the unit fills at ``a* = max(a_t, a_{t+10 s})`` only if the state at ``t + 10 s`` still offers at least ``min_shares`` at
    prices <= ``a*`` (cumulative over the stored best ask levels, ascending) and ``a* <= cap``; otherwise ``None`` (no fill in this check)."""
    levels = sorted((float(p), float(s)) for p, s in (ladder_t10 or []))
    if ask_t is None or not levels:
        return None
    a_star = max(float(ask_t), levels[0][0])
    if a_star > cap:
        return None
    avail = sum(s for p, s in levels if p <= a_star + 1e-12)
    return a_star if avail >= min_shares else None


def _binom_cdf(k: int, n: int, p: float) -> float:
    total = 0.0
    lp, lq = math.log(p), math.log1p(-p)
    for i in range(k + 1):
        total += math.exp(math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) + i * lp + (n - i) * lq)
    return min(total, 1.0)


def clopper_pearson_upper(k: int, n: int, conf: float = TAIL_CONF) -> float:
    """One-sided ``conf`` Clopper-Pearson upper bound for a binomial share: the p with P(X <= k; n, p) = 1 - conf (bisection, 200 steps)."""
    if n <= 0 or k >= n:
        return 1.0
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if _binom_cdf(k, n, mid) > 1.0 - conf:
            lo = mid
        else:
            hi = mid
    return hi


def required_margin(n_days: int, k_losing: int) -> float:
    """Mean gross margin per share (``1 - a - f``) the day-unit tail gate needs at ``n_days`` traded days and ``k_losing`` losing days (a function of the
    counts only; used by the census). With ``W_d = sum(1 - c)``, ``L_d = sum(c)`` and ``c = a + f`` per unit, ``W_d + L_d`` is the day's unit count, so the gate
    ``mean(W)(1 - q_U) - mean(L) q_U >= 0`` is exactly ``mean(W) / mean(units) >= q_U``: the unit-weighted mean margin must be at least ``q_U`` (no equal-cost
    assumption). That is about 7.9c at 56 days with no losing day, 11.3c with one and 14.2c with two (Erratum E1 in CREATIVE_BATCH_8.md: the design text's
    8.4 / 12.5 / 16c came from an arithmetic slip; the gate formula, level and bound are unchanged)."""
    return clopper_pearson_upper(k_losing, n_days)


def tail_gate(days: dict[str, list[tuple[float, float, float]]]) -> dict:
    """The binding day-unit tail gate. ``days`` maps a traded day to its units ``(ask, fee_per_share, y_fav)``. The day's paper book buys one share at
    each traded unit: ``W_d = sum(1 - a - f)`` (gain if nothing loses), ``L_d = sum(a + f)`` (loss if everything loses). A day is losing iff any of its
    units does not win in full (``y_fav < 1``; a 50-50 resolution pays 0.5 and therefore makes its day a losing day). ``q_U`` is the one-sided 99% Clopper-Pearson upper bound of the share of losing days. The gate holds
    iff ``mean_d(W_d) (1 - q_U) - mean_d(L_d) q_U >= 0``."""
    n = len(days)
    if n == 0:
        return {"n_days": 0, "k_losing": 0, "q_u": 1.0, "mean_w": 0.0, "mean_l": 0.0, "value": -math.inf, "passes": False}
    w = [sum(1.0 - a - f for a, f, _ in u) for u in days.values()]
    lo = [sum(a + f for a, f, _ in u) for u in days.values()]
    k = sum(1 for u in days.values() if any(y < 1.0 for _, _, y in u))
    q = clopper_pearson_upper(k, n)
    mw, ml = sum(w) / n, sum(lo) / n
    value = mw * (1.0 - q) - ml * q
    return {"n_days": n, "k_losing": k, "q_u": q, "mean_w": mw, "mean_l": ml, "value": value, "passes": bool(value >= 0.0)}


# ---- rules file ----------------------------------------------------------------------------------------------------------------------------


def _books_declared() -> dict:
    from . import cb8_books as bk  # noqa: PLC0415

    return {"offsets_s": list(bk.OFFSETS_S), "plus_s": [0, LATENCY_S], "top_ask_levels": bk.TOP_LEVELS, "audit": {"seed": bk.AUDIT_SEED, "hour": bk.AUDIT_HOUR, "n_days": bk.AUDIT_DAYS,
            "pass_share": bk.AUDIT_PASS, "available_min_share": bk.AVAILABLE_MIN, "rule": "count per (market, day) whether the condition id has any event; PASS iff >= 90% of pairs"},
            "order": {"seed": bk.ORDER_SEED, "rule": "seeded, alternating SCREEN and HOLDOUT days"}, "ingress_cap_gb": bk.INGRESS_CAP_GB, "lookback": "hour 14Z only for tokens without a book event by t_end - 600 s",
            "prints": {"window_s": [-bk.PRINT_PRE_S, bk.PRINT_POST_S], "pages": bk.PRINT_PAGES, "post_t_end": "guarded file", "wallet": "not stored"},
            "seal": {"name": bk.SEAL_NAME, "copy": bk.SEAL_COPY_NAME, "output_cap_gb": bk.OUTPUT_CAP_GB, "drops": "by id and key against every seal copy committed by then (DROPPED_* blocks)"}}


def declared() -> dict:
    return {
        "population": {"days": f"[{B_FIRST}, {B_END}) minus the pmxt gap [{GAP[0]}, {GAP[1]})", "t_end": "d 16:00:00Z (12:00 EDT)", "gamma_window": list(GAMMA_WINDOW),
                       "endDate_exact": "endDate must equal t_end(d)", "question_re": QUESTION_RE, "flag_res": FLAG_RES, "up_re": UP_RE, "down_re": DOWN_RE,
                       "strike_rule": "mirrored groups; strike date = d - 1; settlement date = d; symbol = asset map", "source_spot_re": SOURCE_SPOT_RE,
                       "source_um_re": SOURCE_UM_RE, "assets": {k: list(v) for k, v in ASSETS.items()}, "outcome_labels": list(OUTCOME_LABELS)},
        "split": {"seed": SEED_SPLIT, "weeks": [WEEKS[0], WEEKS[1]], "rule": "ISO weeks in pairs (16,17)..(30,31): a seeded coin picks which week of the pair is SCREEN; "
                  "week 32 by its own coin", "table": {str(k): v for k, v in sorted(week_split().items())}},
        "features": {"checkpoints_s": list(CHECKPOINTS_S), "reported_checkpoint_s": REPORT_CHECKPOINT_S, "candle_usable_s": CANDLE_USABLE_S, "n_sigma": N_SIGMA,
                     "sigma_min_present": SIGMA_MIN_PRESENT, "z_min": Z_MIN, "fresh_s": FRESH_S, "pre_candle_minutes": PRE_MIN,
                     "strike": "close of the 1m candle opening at t_end(d - 1)", "guarded": ["outcomes_guarded.csv.gz", "klines_settle_guarded.csv.gz"]},
        "units": {"traded": f"best ask <= {BUY_CAP} and size at the ask >= {MIN_SHARES:g}", "buy_cap": BUY_CAP, "latency_s": LATENCY_S,
                  "latency_rule": "fill at max(a_t, a_{t+10 s}) only if >= 5 shares at <= that price remain at t + 10 s (stored best 10 ask levels) and a* <= 0.99"},
        "cost": {"fee": "r a (1 - a), r = max(fee_rate_bps/1e4 of the token's latest pmxt event <= t, economics.DOCS_CATEGORY_RATE['crypto'])",
                 "docs_crypto_rate": econ.DOCS_CATEGORY_RATE["crypto"], "robustness": "+0.75c on a"},
        "gate": {"edge_floor": EDGE_FLOOR, "tail": "day units; W_d = sum(1-a-f), L_d = sum(a+f); losing day = any unit with y_fav < 1 (a 50-50 resolution, y_fav = 0.5, is a losing day); q_U one-sided 99% Clopper-Pearson upper bound "
                 "(bisection) of the losing-day share; mean_d(W_d)(1-q_U) - mean_d(L_d) q_U >= 0", "tail_conf": TAIL_CONF,
                 "source_disagree_max": SOURCE_DISAGREE_MAX},
        "sources": {"binance": {"base": BINANCE_BASE, "months": list(MONTHS), "rps": BINANCE_RPS, "checksum": "<zip>.CHECKSUM sha256", "stored": "pre-t_end candles, strikes, guarded settlement candles"},
                    "pmxt": "cb8_books", "exclusion": {"max_unverified_key_share": MAX_UNVERIFIED_KEY_SHARE, "pins": "cb7_common.EXCLUSION_PINS + committed seal copies at q0164 + REQUIRED extra id pins " + "/".join(REQUIRED_EXTRA_PINS) + " (derived ids CSV with a source-sha sidecar)",
                                                                  "key_types_applied": list(B_KEY_TYPES), "series_key": "waived for B (Amendment 2026-10-23); id, event and neg-risk keys kept; the same set at the seal-time drops",
                                                                  "smoke_accepted_under": list(SMOKE_ACCEPT_SHAS), "run_dirs": [RUN_FRAME, "updown_b"]}},
        "smoke": {"version": SMOKE_VERSION, "seed_pool": SMOKE_SEED_POOL, "seed_pmxt": SMOKE_SEED_PMXT, "n": SMOKE_N, "candidates": SMOKE_CANDIDATES,
                  "pool": f"closed, end in [{SMOKE_END_FROM}, {SMOKE_END_TO}), volume >= {SMOKE_MIN_VOLUME:g}, life >= {SMOKE_MIN_LIFE_DAYS} d",
                  "criterion_a": "one paged day [end-5d, end-4d) at limit 1000 per pool market; rows in bounds, newest first, no duplicate across pages, "
                                 f">= {SMOKE_MIN_NONEMPTY} of {SMOKE_N} non-empty, <= {SMOKE_MAX_CAPPED} capped (10 pages or venue 400 at offset > 0); deep-offset probe at "
                                 f"offset {SMOKE_DEEP_OFFSET}: 400 = capped by the venue, 200 = deep paging works, anything else = failed (criterion not met)",
                  "criterion_b": "Binance .CHECKSUM matches for BTCUSDT spot and HYPEUSDT futures/um 2026-03 (outside the B window), archive parses",
                  "criterion_c": f"pmxt HEAD returns a size for {SMOKE_PMXT_HOURS} seeded B-window 15Z hours",
                  "network_failure": "nothing written, exit 75"},
        "books": _books_declared(),
        "disk": {"frame_output_cap_gb": FRAME_OUTPUT_CAP_GB, "keys_output_cap_gb": KEYS_OUTPUT_CAP_GB, "data_dumps_fetch_cap_gb": cm.DATA_DUMPS_FETCH_CAP_GB},
    }


def rule_funcs() -> tuple:
    return (declared, _books_declared, smoke_pool_ids, smoke_pmxt_hours, _read_exclusion, _month_items, fetch_archive, httpx_blob_get, _num, Pacer.wait, d_of, t_end, all_days, b_days, week_split, day_split, _pd, parse_updown, archive_name, archive_url, parse_checksum, verify_zip,
            kline_rows, extract_month, candle_usable, min_present, z_features, eligible_unit, traded_unit, fee_rate, taker_fee_per_share, unit_net,
            latency_fill, _binom_cdf, _ids_of_file, clopper_pearson_upper, required_margin, tail_gate, updown_row, frame_reason, walk_frame, drop_and_split, binance_fetch,
            finalize_frame, updown_frame, run_smoke, smoke_ok, exclusion_ids_cb8, exclusion_keys, c7.key_types_matched, hb._rank,
            outcome_label_order, derive_exclusion_ids, _extra_pin_sources, source_group, attribution_pins, id_sources_by_group, id_drop_report, compare_archive_meta)


def _dependency_funcs() -> list:
    """Shared functions and classes the B data rules call (hashed so an edit anywhere in the call chain invalidates the rules file)."""
    from . import cb8_flow as flow  # noqa: PLC0415
    from . import history_sources as hs  # noqa: PLC0415

    return [hb.frame_row, c6.key_fields, c6.lookup_keys, c6.exclusion_stage, c7.smoke_pool, c7.load_exclusion_keys, flow.seal_copy_ids, cm.verify_manifest_files, hs.pmxt_url, hs.RangeFile]


def _all_rule_funcs() -> list:
    from . import cb8_books  # noqa: PLC0415

    return list(rule_funcs()) + list(cb8_books.rule_funcs()) + [cm.windowed_prints, cm._parse_print] + _dependency_funcs()


def rules_doc() -> dict:
    funcs = _all_rule_funcs()
    src = "\n".join(inspect.getsource(f) for f in funcs)
    return {"rules_version": RULES_VERSION, "declared": declared(),
            "funcs_sha256": hashlib.sha256(src.encode()).hexdigest(),
            "func_sources_sha256": {f.__qualname__: hashlib.sha256(inspect.getsource(f).encode()).hexdigest() for f in funcs}}


def rules_file_doc() -> dict:
    d = rules_doc()
    return {**d, "rules_sha256": cm.sha_obj(d)}


def write_rules(path: Path) -> Path:
    path = Path(path)
    want = rules_file_doc()
    if path.exists() and json.loads(path.read_text()) != want:
        raise cm.Refused(f"{path} exists with different content; a rules file is never rewritten")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(want, indent=1, sort_keys=True) + "\n")
    return path


def verify_rules(path: Path, *, require_committed: bool = True) -> str:
    """Refuse (exit 2) unless the rules file equals the code's. Returns ``rules_sha256``."""
    path = Path(path)
    if not path.exists():
        raise cm.Refused(f"rules file {path} not found")
    if require_committed:
        from . import cb1_history  # noqa: PLC0415

        if not cb1_history.spec_committed(path):
            raise cm.Refused(f"rules file {path} is not committed (or differs from HEAD)")
    try:
        doc = json.loads(path.read_text())
    except ValueError as exc:
        raise cm.Refused(f"rules file {path} unreadable") from exc
    want = rules_file_doc()
    if doc != want:
        raise cm.Refused(f"rules hash mismatch: file {doc.get('rules_sha256')} != code {want['rules_sha256']}")
    return want["rules_sha256"]


# ---- network helpers (injectable; no network in tests) -----------------------------------------------------------------------------


BlobGet = Callable[[str], tuple[int, bytes]]


def httpx_blob_get(timeout: float = 120.0) -> BlobGet:
    """``(status, bytes)`` of a keyless GET (Binance archive). A transport error raises ``RuntimeError`` (transient; never read as missing)."""

    def get(url: str) -> tuple[int, bytes]:
        import httpx  # noqa: PLC0415

        try:
            r = httpx.get(url, timeout=timeout, headers={"User-Agent": "arepo-research-lab/1"}, follow_redirects=True)
        except httpx.HTTPError as exc:
            raise RuntimeError(f"blob get failed: {type(exc).__name__}") from None
        return r.status_code, r.content

    return get


class Pacer:
    """At most ``rps`` calls a second on a plain callable (Binance archive etiquette)."""

    def __init__(self, rps: float = BINANCE_RPS, sleep: Callable[[float], None] = time.sleep, clock: Callable[[], float] = time.monotonic) -> None:
        self.gap, self.sleep, self.clock, self.last, self.calls = 1.0 / rps, sleep, clock, -1e9, 0

    def wait(self) -> None:
        w = self.gap - (self.clock() - self.last)
        if w > 0:
            self.sleep(w)
        self.last = self.clock()
        self.calls += 1


def fetch_archive(get: BlobGet, pacer: Pacer, symbol: str, venue: str, yyyymm: str) -> tuple[bytes, str]:
    """Download one monthly archive and its ``.CHECKSUM``; return (zip bytes, verified sha256). 404 or a mismatch is a :class:`cm.Refused`;
    other statuses raise ``RuntimeError`` (transient)."""
    url = archive_url(symbol, venue, yyyymm)
    pacer.wait()
    st, chk = get(url + ".CHECKSUM")
    if st == 404:
        raise cm.Refused(f"checksum file for {archive_name(symbol, yyyymm)} not found")
    if st != 200:
        raise RuntimeError(f"checksum status {st}")
    pacer.wait()
    st, z = get(url)
    if st == 404:
        raise cm.Refused(f"archive {archive_name(symbol, yyyymm)} not found")
    if st != 200:
        raise RuntimeError(f"archive status {st}")
    return z, verify_zip(z, chk.decode("utf-8", "replace"))


# ---- q0161 smoke ------------------------------------------------------------------------------------------------------------------------


def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return float("nan")


def smoke_pool_ids(files: dict[str, Path], pins, n_candidates: int = SMOKE_CANDIDATES, seed: str = SMOKE_SEED_POOL) -> list[str]:
    return c7.smoke_pool(files, pins, n_candidates, seed)


def smoke_pmxt_hours(seed: str = SMOKE_SEED_PMXT, n: int = SMOKE_PMXT_HOURS) -> list[str]:
    """``n`` B-window 15Z hour files (by day) in seeded order."""
    return sorted(b_days(), key=lambda d: hb._rank(seed, d))[:n]


def run_smoke(lim: hb.Limiter, files: dict[str, Path], pins, rules_sha: str, *, blob_get: BlobGet, size_fn: Callable[[str], int], pacer: Pacer | None = None,
              pmxt_url: Callable[[datetime], str] | None = None) -> dict:
    """q0161, counts only. A network failure (retries exhausted, a non-200 Gamma / trades status other than the probes) raises
    :class:`cm.NotNow` and nothing is written."""
    from . import history_sources as hs  # noqa: PLC0415

    pmxt_url = pmxt_url or hs.pmxt_url
    pacer = pacer or Pacer()
    cands = smoke_pool_ids(files, pins)
    found: dict[str, dict] = {}
    n_gamma = 0
    for i in range(0, len(cands), c7.GAMMA_IDS_PER_REQUEST):
        batch = cands[i:i + c7.GAMMA_IDS_PER_REQUEST]
        try:
            status, rows = lim.get(hb.GAMMA_MARKETS, {"id": batch, "limit": c7.GAMMA_IDS_PER_REQUEST, "closed": "true"})
        except RuntimeError:
            raise cm.NotNow("smoke: Gamma lookup failed after retries (network); nothing written, retry later") from None
        n_gamma += 1
        if status != 200 or not isinstance(rows, list):
            raise cm.NotNow(f"smoke: Gamma lookup status {status}; nothing written, retry later")
        for m in rows:  # parse guard: end, creation, volume and the condition id only
            if isinstance(m, dict) and str(m.get("id")) in batch:
                found[str(m["id"])] = {"end": c4._parse_ts(m.get("endDate")), "created": c4._parse_ts(m.get("createdAt")) or c4._parse_ts(m.get("startDate")),
                                       "vol": _num(m.get("volumeNum")), "cid": m.get("conditionId"), "closed": bool(m.get("closed"))}
    lo, hi = cm.ep(SMOKE_END_FROM), cm.ep(SMOKE_END_TO)
    pool = [x for x in cands if x in found and found[x]["closed"] and found[x]["end"] is not None and lo <= found[x]["end"] < hi
            and found[x]["vol"] >= SMOKE_MIN_VOLUME and found[x]["cid"] and found[x]["created"] is not None
            and found[x]["end"] - found[x]["created"] >= SMOKE_MIN_LIFE_DAYS * cm.DAY]
    chosen = pool[:SMOKE_N]
    n_nonempty = n_capped = n_failed = 0
    bounds_ok = order_ok = dup_ok = True
    api_error = None
    for x in chosen:
        end = int(found[x]["end"])
        a, b = end - 5 * 86400, end - 4 * 86400 - 1
        try:
            rows, info = cm.windowed_prints(lim, found[x]["cid"], a, b, SMOKE_DAY_PAGES, b"cb8-smoke-no-wallets", limit=PRINT_LIMIT)
        except cm.ApiError as exc:
            n_failed += 1
            api_error = str(exc)[:80]
            continue
        except RuntimeError:
            raise cm.NotNow("smoke: trades request failed after retries (network); nothing written, retry later") from None
        n_capped += int(info["capped"])
        n_nonempty += int(bool(rows))
        bounds_ok = bounds_ok and info["out_of_window"] == 0 and info["malformed"] == 0
        order_ok = order_ok and info["order_ok"]
        dup_ok = dup_ok and info["duplicates"] == 0
    probe = {"status": None, "verdict": "not_run", "market_id": None}
    if chosen:  # deep-offset probe: capped by the venue (400) is distinguished from a failed request (anything else)
        x = chosen[0]
        end = int(found[x]["end"])
        try:
            st, data = lim.get(hb.DATA_TRADES, {"market": found[x]["cid"], "start": end - 35 * 86400, "end": end, "takerOnly": "true", "limit": PRINT_LIMIT,
                                                "offset": SMOKE_DEEP_OFFSET})
        except RuntimeError:
            raise cm.NotNow("smoke: deep-offset probe failed after retries (network); nothing written, retry later") from None
        verdict = "capped_by_venue" if st == 400 else ("deep_ok" if st == 200 and isinstance(data, list) else "failed")
        probe = {"status": st, "verdict": verdict, "market_id": x, "n_rows": len(data) if st == 200 and isinstance(data, list) else None}
    full = len(chosen) >= SMOKE_N
    crit_a = bool(full and n_failed == 0 and bounds_ok and order_ok and dup_ok and n_nonempty >= SMOKE_MIN_NONEMPTY and n_capped <= SMOKE_MAX_CAPPED
                  and probe["verdict"] in ("capped_by_venue", "deep_ok"))
    bin_res = []
    for sym, venue, ym in SMOKE_BINANCE:
        try:
            z, sha = fetch_archive(blob_get, pacer, sym[:-4], venue, ym)
            n_rows = sum(1 for _ in kline_rows(z))
            bin_res.append({"symbol": sym, "venue": venue, "month": ym, "checksum_ok": True, "n_rows": n_rows, "sha256": sha})
        except cm.Refused as exc:
            bin_res.append({"symbol": sym, "venue": venue, "month": ym, "checksum_ok": False, "reason": str(exc)[:100], "n_rows": 0})
        except RuntimeError:
            raise cm.NotNow("smoke: Binance archive request failed (network); nothing written, retry later") from None
    crit_b = all(r["checksum_ok"] and r["n_rows"] > 0 for r in bin_res)
    heads = []
    for d in smoke_pmxt_hours():
        url = pmxt_url(datetime.fromisoformat(f"{d}T15:00:00+00:00"))
        try:
            heads.append({"day": d, "size": int(size_fn(url))})
        except FileNotFoundError:
            heads.append({"day": d, "size": None, "reason": "not_published"})
        except Exception:
            raise cm.NotNow("smoke: pmxt HEAD failed (network); nothing written, retry later") from None
    crit_c = len(heads) >= SMOKE_PMXT_HOURS and all(h["size"] for h in heads)
    return {"smoke_version": SMOKE_VERSION, "rules_sha256": rules_sha, "git_commit": hb._git_commit(), "run_utc": cm.iso(time.time()), "counts_only": True,
            "criterion_a_data_api_paging": crit_a, "criterion_b_binance_checksum": crit_b, "criterion_c_pmxt_heads": crit_c,
            "pass": bool(crit_a and crit_b and crit_c), "n_candidates": len(cands), "n_found_on_gamma": len(found), "n_in_pool": len(pool),
            "n_requested": len(chosen), "n_nonempty": n_nonempty, "n_capped": n_capped, "n_failed_requests": n_failed, "last_api_error": api_error,
            "bounds_ok": bounds_ok, "newest_first_ok": order_ok, "no_duplicates_ok": dup_ok, "n_gamma_requests": n_gamma, "deep_offset_probe": probe,
            "binance": bin_res, "pmxt_heads": heads,
            "pass_thresholds": {"n": SMOKE_N, "min_nonempty": SMOKE_MIN_NONEMPTY, "max_capped": SMOKE_MAX_CAPPED, "deep_offset": SMOKE_DEEP_OFFSET}}


def smoke_ok(path: Path, rules_sha: str, need: tuple[str, ...] = ("b", "c")) -> dict:
    """The B fetchers' smoke gate: the result exists, was made under the same rules hash, and the criteria in ``need`` hold (default b and c)."""
    p = Path(path)
    if not p.exists():
        raise cm.Refused(f"smoke result {p} not found; run the CB8 smoke first")
    try:
        d = json.loads(p.read_text())
    except ValueError as exc:
        raise cm.Refused(f"smoke result {p} unreadable") from exc
    if d.get("smoke_version") != SMOKE_VERSION:
        raise cm.Refused(f"smoke result {p} is {d.get('smoke_version')}, not {SMOKE_VERSION}")
    if d.get("rules_sha256") != rules_sha and d.get("rules_sha256") not in SMOKE_ACCEPT_SHAS:
        raise cm.Refused(f"smoke result {p} was made under another rules hash")
    keys = {"a": "criterion_a_data_api_paging", "b": "criterion_b_binance_checksum", "c": "criterion_c_pmxt_heads"}
    bad = [k for k in need if d.get(keys[k]) is not True]
    if bad:
        raise cm.Refused(f"smoke result {p}: criteria {bad} not met; B is 'not run (source)'")
    return d


# ---- q0164 exclusion keys ----------------------------------------------------------------------------------------------------------------


def _ids_of_file(p: Path) -> set[str]:
    if str(p).endswith(".gz"):
        return {str(r["market_id"]) for r in c7.read_csv_gz(p)}
    with Path(p).open(encoding="utf-8", newline="") as fh:
        return {str(r["market_id"]) for r in csv.DictReader(fh)}


def exclusion_ids_cb8(files: dict[str, Path], pins) -> set[str]:
    """Market ids of every pinned file: ``market_id`` column of sample / ids files, and the ids named in a seal copy."""
    ids: set[str] = set()
    w = c4._cb2w()
    for pin in pins:
        p = files[pin["name"]]
        if pin["kind"] in ("sample", "ids"):
            ids.update(_ids_of_file(p))
        else:
            ids |= w.seal_ids_from_copy(p)
    return ids


def derive_exclusion_ids(kind: str, src: Path, out_csv: Path) -> dict:
    """Derive an ids CSV (``market_id`` column, sorted, unique) for a required q0164 extra pin and its sidecar ``<out>.meta.json`` (source path, the source's
    sha256, counts, the ids file's sha256). ``c1_legs``: ``src`` = ``cross_venue/matches.json`` (ids = ``p_market_id`` of every row; the whole selection, a
    superset of the 316-pair C1 set). ``cb5_listings``: ``src`` = the ``cb5_extract/listings`` directory (ids = ``market_id`` of every ``*.csv.gz``; the source
    sha256 is the sha256 of the sorted ``name<TAB>sha256`` lines). Ids only are read. Write-once: an existing different output is a refusal."""
    src, out_csv = Path(src), Path(out_csv)
    ids: set[str] = set()
    n_rows = 0
    if kind == "c1_legs":
        if not src.is_file():
            raise cm.Refused(f"{src} is not a file")
        doc = json.loads(src.read_text())
        if not isinstance(doc, list) or not doc:
            raise cm.Refused(f"{src}: expected a non-empty list of pairs")
        for r in doc:
            n_rows += 1
            if isinstance(r, dict) and str(r.get("p_market_id") or "").strip():
                ids.add(str(r["p_market_id"]).strip())
        source_sha, n_files = h5_seal.sha256_file(src), 1
    elif kind == "cb5_listings":
        files = sorted(src.glob("*.csv.gz")) if src.is_dir() else []
        if not files:
            raise cm.Refused(f"{src} holds no *.csv.gz listing files")
        lines = []
        for f in files:
            lines.append(f"{f.name}\t{h5_seal.sha256_file(f)}")
            for r in c7.read_csv_gz(f):
                n_rows += 1
                if str(r.get("market_id") or "").strip():
                    ids.add(str(r["market_id"]).strip())
        source_sha, n_files = hashlib.sha256("\n".join(lines).encode()).hexdigest(), len(files)
    else:
        raise cm.Refused(f"unknown pin kind {kind!r}")
    if not ids:
        raise cm.Refused(f"{src}: no market ids found")
    body = ("market_id\n" + "\n".join(sorted(ids)) + "\n").encode()
    meta = {"kind": kind, "source_path": str(src), "source_sha256": source_sha, "n_source_files": n_files, "n_rows": n_rows, "n_ids": len(ids),
            "ids_sha256": hashlib.sha256(body).hexdigest(), "ids_only": True}
    metap = out_csv.with_name(out_csv.name + ".meta.json")
    for path, data in ((out_csv, body), (metap, (json.dumps(meta, indent=1, sort_keys=True) + "\n").encode())):
        if path.exists() and path.read_bytes() != data:
            raise cm.Refused(f"{path} exists with different content; a derived pin is never rewritten")
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_csv.write_bytes(body)
    metap.write_bytes((json.dumps(meta, indent=1, sort_keys=True) + "\n").encode())
    return meta


def _extra_pin_sources(extra_pins: list[dict], required: tuple[str, ...]) -> dict[str, dict]:
    """Refuse unless every required extra pin is present with a sidecar whose ``ids_sha256`` equals the pin's sha256 and that records the source sha256."""
    have = {p["name"]: p for p in extra_pins}
    missing = [n for n in required if n not in have]
    if missing:
        raise cm.Refused(f"q0164 needs the extra id pins {missing} (design 1.3: C1 legs, CB5 listings); q0164 cannot be re-run, so it refuses without them")
    out: dict[str, dict] = {}
    for n in required:
        mp = Path(have[n]["path"]).with_name(Path(have[n]["path"]).name + ".meta.json")
        if not mp.exists():
            raise cm.Refused(f"extra pin {n}: sidecar {mp} not found; derive the ids file with 'derive-exclusion-ids'")
        meta = json.loads(mp.read_text())
        if meta.get("ids_sha256") != have[n]["sha256"] or not meta.get("source_sha256"):
            raise cm.Refused(f"extra pin {n}: sidecar does not match the pinned sha256 or records no source sha256")
        out[n] = {k: meta.get(k) for k in ("kind", "source_path", "source_sha256", "n_source_files", "n_ids")}
    return out


def exclusion_keys(out_root: Path, transport, *, rules_sha: str, history_root: Path, seals_dir: Path | None = None, extra_pins: list[dict] | None = None,
                   rps: float = 4.0, disk_cap: int = int(KEYS_OUTPUT_CAP_GB * 1024**3), budget_min: float | None = None, now: float | None = None,
                   sleep=time.sleep, live_check=None, should_stop: Callable[[], bool] | None = None, wall_clock: Callable[[], float] = time.time,
                   snapshot_root: Path | None = None, health_check=None, data_dumps: Path | None = None,
                   data_dumps_cap_gb: float = cm.DATA_DUMPS_FETCH_CAP_GB, dest_dir: Path | None = None, required_extra: tuple[str, ...] = REQUIRED_EXTRA_PINS) -> dict:
    """q0164. Gamma lookup by id (<= 50 per request, ``closed=true`` retry, parse guard keeps ids and keys) of the ids in the sha-pinned h1/h2/h3/h5/h5_ladders
    files, every other committed ``*_SEAL.json`` under ``seals_dir`` (hash recorded at the start; the known later seals that are absent are recorded as
    "absent at q0164") and ``extra_pins`` (``{"name","kind":"ids","path","sha256"}``, a CSV with a ``market_id`` column). The finished files are copied
    byte-for-byte to ``dest_dir`` (default ``creative_batch8/``). More than 2% of ids without metadata -> ``disjointness_unverified``."""
    out_root, seals_dir = Path(out_root), Path(seals_dir or cm.SEALS_DIR)
    cm.refuse_path(out_root)
    extra_src = _extra_pin_sources([dict(p) for p in (extra_pins or [])], required_extra)
    cm.require_room(data_dumps, data_dumps_cap_gb, disk_cap)
    pins = list(c7.EXCLUSION_PINS) + [dict(p) for p in (extra_pins or [])]
    base_names = {Path(p["path"]).name for p in c7.EXCLUSION_PINS if p["kind"] == "seal"}
    absent, dyn = [], []
    for p in sorted(seals_dir.glob("*_SEAL.json")):
        if p.name in base_names or p.name in ("h9_flow_SEAL.json", "cb8_updown_holdout_SEAL.json"):
            continue
        dyn.append({"name": p.stem, "kind": "seal", "path": str(p), "sha256": h5_seal.sha256_file(p)})
    for known in ("h6_weather_SEAL.json", "h7_cb4_era_SEAL.json", "h7_cb4_series_SEAL.json", "h8_tail_SEAL.json", "h8_text_SEAL.json", "h8_geo_SEAL.json"):
        if not (seals_dir / known).exists():
            absent.append(known)
    pins += dyn
    files = c6.verify_exclusion_files(pins, history_root=Path(history_root), seals_dir=seals_dir,
                                      seal_paths={Path(p['path']).name: Path(p['path']) for p in (extra_pins or [])})
    ids = exclusion_ids_cb8(files, pins)
    fr = cm.open_run(out_root, RUN_KEYS, transport, allowed_run_id=RUN_KEYS, kind="cb8_exclusion_keys", label="CB8 exclusion keys",
                     params={"n_ids": len(ids), "pins": [{k: p[k] for k in ("name", "kind", "sha256")} for p in pins], "absent_at_q0164": absent,
                             "extra_pin_sources": extra_src, "key_types": list(c7.KEY_TYPES), "evidence_role": "exploratory_historical"},
                     rules_sha=rules_sha, key_fp="", disk_cap=disk_cap, rps=rps, budget_min=budget_min, now=now, sleep=sleep, live_check=live_check,
                     wall_clock=wall_clock, snapshot_root=snapshot_root, health_check=health_check)
    dest = Path(dest_dir) if dest_dir is not None else cm.CB8_DIR
    why = fr.unhealthy()
    if why:
        m = fr.manifest(why, {"transient": True})
        m["status"] = "in_progress"
        return m
    try:
        rep, stopped = c6.exclusion_stage(fr, ids, should_stop)
    except OSError as exc:
        return cm.disk_budget_end(fr, exc)
    except RuntimeError as exc:
        m = fr.manifest(f"stage_failed: {exc}"[:200], {"transient": True})
        m["status"] = "in_progress"
        return m
    if stopped:
        m = fr.manifest(stopped, {"transient": True})
        m["status"] = "in_progress"
        return m
    assert rep is not None
    rep = {**rep, "absent_at_q0164": absent, "extra_pin_sources": extra_src, "pins": [{k: p[k] for k in ("name", "kind", "sha256")} for p in pins]}
    (fr.rdir / "exclusion_report.json").write_text(json.dumps(rep, indent=1, sort_keys=True))
    dest.mkdir(parents=True, exist_ok=True)
    for name in ("exclusion_keys.csv.gz", "exclusion_report.json"):
        tmp = dest / (name + ".tmp")
        shutil.copyfile(fr.rdir / name, tmp)
        tmp.replace(dest / name)
        fr.record_file(fr.rdir / name)
    status = UNVERIFIED if rep["disjointness"] == UNVERIFIED else KEYS_COMPLETE
    m = fr.manifest(None, {"exclusion_report": rep, "status": status, "complete": True})
    m["status"] = status
    return m


# ---- q0165: frame -----------------------------------------------------------------------------------------------------------------------


FRAME_COLUMNS = ["market_id", "condition_id", "token_up", "token_down", "event_id", "event_ids", "neg_risk_market_id", "series_ids", "asset", "symbol", "venue",
                 "day", "week", "split", "question", "desc_sha256", "resolution_source", "end_at", "created_at", "closed", "closed_time"]
GUARDED_OUTCOME_COLUMNS = ["market_id", "day", "outcome_labels", "outcome_prices", "uma_status"]  # labels give the order of outcome_prices (Up/Down or Down/Up)
PRE_COLUMNS = ["asset", "day", "open_ms", "close"]
STRIKE_COLUMNS = ["asset", "day", "strike_close", "strike_open_ms"]
SETTLE_COLUMNS = ["asset", "day", "open_ms", "close"]


def updown_row(m: dict, day: str) -> tuple[dict | None, str]:
    """``(frame row, "")`` of one Gamma market that ends on ``day``, or ``(None, reason)``. Outcome prices are not part of the row."""
    if not re.match(QUESTION_RE, str(m.get("question") or "")):
        return None, "question_pattern"
    r = hb.frame_row(m, with_text=False, with_outcomes=True)
    if r is None:
        return None, "not_binary"
    try:
        labels = json.loads(m["outcomes"]) if isinstance(m.get("outcomes"), str) else m.get("outcomes")
    except ValueError:
        labels = None
    if not (isinstance(labels, list) and len(labels) == 2 and sorted(map(str, labels)) == sorted(OUTCOME_LABELS)):
        return None, "outcome_labels"
    ee = r["end_epoch"]
    if not (ee == ee) or ee != t_end(day):
        return None, "end_not_1600z"
    desc = str(m.get("description") or "")
    p = parse_updown(m.get("question"), desc, m.get("resolutionSource"), day)
    if not p["ok"]:
        return None, p["reason"]
    k = c6.key_fields(m)
    toks = json.loads(m["clobTokenIds"])
    up_first = str(labels[0]) == "Up"
    row = {"market_id": r["market_id"], "condition_id": r["condition_id"], "token_up": toks[0] if up_first else toks[1], "token_down": toks[1] if up_first else toks[0],
           "event_id": r["event_id"], "event_ids": k["event_ids"], "neg_risk_market_id": k["neg_risk_market_id"], "series_ids": k["series_ids"], "asset": p["asset"],
           "symbol": p["symbol"], "venue": p["venue"], "day": day, "week": d_of(day).isocalendar()[1], "split": day_split(day),
           "question": str(m.get("question"))[:120], "desc_sha256": hashlib.sha256(desc.encode()).hexdigest(), "resolution_source": str(m.get("resolutionSource") or "")[:120],
           "end_at": r["end_at"], "created_at": r["created_at"], "closed": r["closed"], "closed_time": r["closed_time"]}
    return row, ""


def outcome_label_order(m: dict) -> str:
    """The market's outcome labels in Gamma order joined by ``|`` (``Up|Down`` or ``Down|Up``): the order of ``outcomePrices`` for the guarded file."""
    try:
        labels = json.loads(m["outcomes"]) if isinstance(m.get("outcomes"), str) else m.get("outcomes")
    except ValueError:
        labels = None
    return "|".join(str(x) for x in labels) if isinstance(labels, list) else ""


def frame_reason(m: dict, day: str) -> str:
    return updown_row(m, day)[1]


def walk_frame(fr: cm.Cb8Run, days: list[str], should_stop: Callable[[], bool] | None = None) -> str | None:
    """Per day one gzip member in ``frame_partial_guarded.jsonl.gz`` (frame rows, guarded outcomes, reason counts). A failed day is retried by a later chunk (3
    attempts). Returns a stop reason or ``None`` when every day is done."""
    pp, pf = fr.rdir / "frame_partial_guarded.jsonl.gz", fr.rdir / "frame_fail.jsonl"
    done = {rec["day"] for rec in c6.iter_partial(pp)}
    fails = c7.walk_failed_days(pf)
    for d in days:
        if d in done or fails.get(d, 0) >= cm.MAX_ITEM_ATTEMPTS:
            continue
        why = fr.stop_reason(should_stop)
        if why:
            return why
        params = {"closed": "true", "order": "id", "ascending": "true", "end_date_min": f"{d}T{GAMMA_WINDOW[0]}Z", "end_date_max": f"{d}T{GAMMA_WINDOW[1]}Z"}
        batch, capped, failed = c4._paged_strict(fr.lim, params, hb.GAMMA_OFFSET_CAP)
        if failed:
            with pf.open("a") as fh:
                fh.write(json.dumps({"day": d}) + "\n")
            fr.counts["frame_request_failures"] = fr.counts.get("frame_request_failures", 0) + 1
            continue
        rows, guarded, reasons = [], [], {}
        for m in batch:
            if not isinstance(m, dict):
                continue
            row, reason = updown_row(m, d)
            if row is None:
                reasons[reason] = reasons.get(reason, 0) + 1
                continue
            rows.append(row)
            guarded.append([row["market_id"], d, outcome_label_order(m), str(m.get("outcomePrices") or ""), str(m.get("umaResolutionStatus") or "")])
        c7.append_member(fr, pp, {"day": d, "rows": rows, "guarded": guarded, "n_raw": len(batch), "capped": bool(capped), "reasons": reasons})
    fails = c7.walk_failed_days(pf)
    done = {rec["day"] for rec in c6.iter_partial(pp)}
    return None if all(d in done or fails.get(d, 0) >= cm.MAX_ITEM_ATTEMPTS for d in days) else "frame_paused"


def source_group(name: str) -> str:
    """The reporting group of an exclusion pin (ruling condition 4): h1/h2/h3, h5, CB5, C1, other seals."""
    if name in ("h1_first", "h2_main", "h3_power"):
        return "h1_h2_h3"
    if name in ("h5_cb1", "h5_cb1_ladders"):
        return "h5"
    if name == "cb5_listings":
        return "CB5"
    if name == "c1_legs":
        return "C1"
    return "other_seals"


def attribution_pins(seals_dir: Path, extra_pins: list[dict] | None = None) -> list[dict]:
    """The pin list behind the exclusion keys, for the id-drop source report only: the fixed pins, every other committed ``*_SEAL.json`` and the extra id pins."""
    seals_dir = Path(seals_dir)
    base_names = {Path(p["path"]).name for p in c7.EXCLUSION_PINS if p["kind"] == "seal"}
    dyn = [{"name": p.stem, "kind": "seal", "path": str(p), "sha256": h5_seal.sha256_file(p)} for p in sorted(seals_dir.glob("*_SEAL.json"))
           if p.name not in base_names and p.name not in ("h9_flow_SEAL.json", "cb8_updown_holdout_SEAL.json")]
    return list(c7.EXCLUSION_PINS) + [dict(p) for p in (extra_pins or [])] + dyn


def id_sources_by_group(files: dict[str, Path], pins: list[dict]) -> dict[str, set[str]]:
    """Market ids of each pin grouped by ``source_group``. A composite seal id ``<market>__<event>`` counts as its numeric market part."""
    out: dict[str, set[str]] = {}
    for pin in pins:
        ids = {i.split("__")[0] for i in exclusion_ids_cb8(files, [pin])}
        out.setdefault(source_group(pin["name"]), set()).update(ids)
    return out


def id_drop_report(dropped: list[dict], id_sources: dict[str, set[str]] | None) -> dict:
    """Ruling condition 4. Id drops by source pin group and the number of distinct days they cover, plus the descriptive B1 sensitivity list (days on which
    an id-dropped Up/Down market settled). Frame fields only (id, day); no price and no outcome. Binding nothing."""
    days = sorted({r["day"] for r in dropped})
    out: dict = {"n_id_dropped": len(dropped), "n_distinct_days": len(days), "day_exclusion_sensitivity_days": days,
                 "use": "descriptive only: the B1 sensitivity that leaves out these days binds nothing (ruling condition 4)"}
    if id_sources is None:
        out["by_source"] = None
        out["source_attribution"] = "unavailable (no source pins given)"
        return out
    by: dict[str, dict] = {}
    for g in sorted(id_sources):
        hit = [r for r in dropped if r["market_id"] in id_sources[g]]
        by[g] = {"n_markets": len(hit), "n_distinct_days": len({r["day"] for r in hit})}
    out["by_source"] = by
    out["n_unattributed"] = sum(1 for r in dropped if not any(r["market_id"] in v for v in id_sources.values()))
    out["note"] = "a market named by several sources counts in each; n_unattributed = id-dropped but in no listed pin (e.g. a pin changed since q0164 or the pred_* market ids)"
    return out


def drop_and_split(rows: list[dict], excl_ids: set[str], excl_keys: dict[str, set[str]], key_types: tuple[str, ...] = B_KEY_TYPES,
                   id_sources: dict[str, set[str]] | None = None) -> tuple[list[dict], dict]:
    """Drop markets that share an id or a key of a type in ``key_types`` with the exclusion set (before the split), count by key type, and report the
    SCREEN / HOLDOUT counts. v3: ``key_types`` = id, event and neg-risk (the series key is waived for B); the id check comes first."""
    rep: dict = {"n_in": len(rows), "dropped_id": 0, "dropped_keys": {}, "key_types_applied": list(key_types)}
    kept, id_dropped = [], []
    for r in rows:
        if r["market_id"] in excl_ids:
            rep["dropped_id"] += 1
            id_dropped.append(r)
            continue
        kt = [t for t in c7.key_types_matched(r, excl_keys) if t in key_types]
        if kt:
            for t in kt:
                rep["dropped_keys"][t] = rep["dropped_keys"].get(t, 0) + 1
            continue
        kept.append(r)
    rep["n_kept"] = len(kept)
    rep["id_drop_report"] = id_drop_report(id_dropped, id_sources)
    rep["by_split"] = {s: sum(1 for r in kept if r["split"] == s) for s in ("screen", "holdout")}
    rep["by_asset"] = {a: sum(1 for r in kept if r["asset"] == a) for a in sorted({r["asset"] for r in kept})}
    rep["days_by_split"] = {s: len({r["day"] for r in kept if r["split"] == s}) for s in ("screen", "holdout")}
    return kept, rep


def _read_exclusion(keys_path: Path) -> tuple[set[str], dict[str, set[str]], dict, str]:
    sets, rep, sha = c7.load_exclusion_keys(keys_path)
    ids = {str(r["market_id"]) for r in c7.read_csv_gz(keys_path)}
    return ids, sets, rep, sha


def _month_items() -> list[dict]:
    return [{"key": f"{a}|{ym}", "asset": a, "symbol": ASSETS[a][0], "venue": ASSETS[a][1], "month": ym} for a in ASSETS for ym in MONTHS]


def binance_fetch(fr: cm.Cb8Run, get: BlobGet, pacer: Pacer, should_stop: Callable[[], bool] | None = None) -> str | None:
    """One partial member per (asset, month): the verified archive's derived rows only (pre-t_end candles, guarded settlement candles); nothing else is
    kept and the zip is not stored. A checksum mismatch or a missing archive is a failed attempt; after 3 the run ends ``source_unverified``."""
    part, pf = fr.rdir / "klines_partial.jsonl.gz", fr.rdir / "klines_fail.jsonl"
    done = {rec["key"] for rec in c6.iter_partial(part)}
    fails: dict[str, int] = {}
    if pf.exists():
        for line in pf.read_text().splitlines():
            if line.strip():
                k = json.loads(line)["key"]
                fails[k] = fails.get(k, 0) + 1
    days = all_days()
    retry = False
    for it in _month_items():
        k = it["key"]
        if k in done:
            continue
        if fails.get(k, 0) >= cm.MAX_ITEM_ATTEMPTS:
            return SOURCE_UNVERIFIED
        why = fr.stop_reason(should_stop)
        if why:
            return why
        month_days = [d for d in days if d.startswith(it["month"])]
        try:
            z, sha = fetch_archive(get, pacer, it["symbol"], it["venue"], it["month"])
            ext = extract_month(kline_rows(z), month_days)
            rec = {"key": k, "asset": it["asset"], "month": it["month"], "zip_sha256": sha, "zip_bytes": len(z), **ext}
        except (cm.Refused, RuntimeError, zipfile.BadZipFile) as exc:
            fails[k] = fails.get(k, 0) + 1
            with pf.open("a") as fh:
                fh.write(json.dumps({"key": k, "error": str(exc)[:120]}) + "\n")
            fr.counts["archive_failures"] = fr.counts.get("archive_failures", 0) + 1
            if fails[k] >= cm.MAX_ITEM_ATTEMPTS:
                return SOURCE_UNVERIFIED
            retry = True
            continue
        c7.append_member(fr, part, rec)
        done.add(k)
        fr.counts["archives_done"] = fr.counts.get("archives_done", 0) + 1
    return "pending_retry" if retry else None


def compare_archive_meta(prior: dict | None, current: dict) -> dict:
    """Ruling condition 2: Binance archives of the earlier frame run may be reused only if their zip sha256 values match its recorded ``archives`` meta.
    The zips and the derived rows were not kept, so nothing is reused: every archive is fetched again and verified against Binance's own CHECKSUM. This
    only records, per (asset|month) key, whether the refetched zip sha256 equals the earlier run's recorded one (``None`` prior -> not compared)."""
    if prior is None:
        return {"compared": False, "reused": False}
    keys = sorted(set(prior) | set(current))
    match = {k: bool(k in prior and k in current and prior[k].get("zip_sha256") == current[k].get("zip_sha256")) for k in keys}
    return {"compared": True, "reused": False, "n_keys": len(keys), "n_match": sum(match.values()), "all_match": all(match.values()),
            "mismatched_keys": [k for k, v in match.items() if not v]}


def finalize_frame(fr: cm.Cb8Run, rdir: Path, days: list[str]) -> dict:
    """Write the feature, strike and guarded files from the partials, hash everything, drop the partials. Returns counts."""
    part = rdir / "klines_partial.jsonl.gz"
    pre, settle = [], {}
    meta = {}
    for rec in c6.iter_partial(part):
        asset = rec["asset"]
        pre += [[asset, d, o, c] for d, o, c in rec["pre"]]
        for d, o, c in rec["settle"]:
            settle[(asset, d)] = (o, c)
        meta[rec["key"]] = {"zip_sha256": rec["zip_sha256"], "n_rows": rec["n_rows"], "first_ms": rec["first_ms"], "last_ms": rec["last_ms"]}
    bset = set(days)
    pre = sorted(r for r in pre if r[1] in bset)
    strikes, missing_strike = [], 0
    for a in ASSETS:
        for d in days:
            prev = (d_of(d) - timedelta(days=1)).isoformat()
            s = settle.get((a, prev))
            if s is None:
                missing_strike += 1
                continue
            strikes.append([a, d, s[1], s[0]])
    hold = rdir / HOLDOUT_SUBDIR
    hold.mkdir(parents=True, exist_ok=True)
    pre_s, pre_h = [r for r in pre if day_split(r[1]) == "screen"], [r for r in pre if day_split(r[1]) == "holdout"]
    str_s, str_h = [r for r in strikes if day_split(r[1]) == "screen"], [r for r in strikes if day_split(r[1]) == "holdout"]
    fr.budget.write_gz_csv(rdir / "klines_pre.csv.gz", PRE_COLUMNS, pre_s)  # SCREEN days only
    fr.budget.write_gz_csv(rdir / "strikes.csv.gz", STRIKE_COLUMNS, str_s)
    fr.budget.write_gz_csv(hold / "klines_pre.csv.gz", PRE_COLUMNS, pre_h)  # HOLDOUT days: sealed with the book states (listed by cb8_books.seal_holdout)
    fr.budget.write_gz_csv(hold / "strikes.csv.gz", STRIKE_COLUMNS, str_h)
    fr.budget.write_gz_csv(rdir / "klines_settle_guarded.csv.gz", SETTLE_COLUMNS, ([a, d, o, c] for (a, d), (o, c) in sorted(settle.items())))
    guarded = [g for rec in c6.iter_partial(rdir / "frame_partial_guarded.jsonl.gz") for g in rec["guarded"]]
    kept = {r["market_id"] for r in c7.read_csv_gz(rdir / "frame.csv.gz")}
    fr.budget.write_gz_csv(rdir / "outcomes_guarded.csv.gz", GUARDED_OUTCOME_COLUMNS, sorted(g for g in guarded if g[0] in kept))
    for name in ("frame.csv.gz", "split.json", "klines_pre.csv.gz", "strikes.csv.gz", "klines_settle_guarded.csv.gz", "outcomes_guarded.csv.gz",
                 f"{HOLDOUT_SUBDIR}/klines_pre.csv.gz", f"{HOLDOUT_SUBDIR}/strikes.csv.gz"):
        fr.record_file(rdir / name)
    part.unlink(missing_ok=True)
    (rdir / "klines_fail.jsonl").unlink(missing_ok=True)
    (rdir / "frame_partial_guarded.jsonl.gz").unlink(missing_ok=True)
    (rdir / "frame_fail.jsonl").unlink(missing_ok=True)
    fr.extra_state["archives"] = meta
    return {"n_pre_rows": len(pre), "n_pre_rows_holdout": len(pre_h), "n_strikes": len(strikes), "n_strikes_holdout": len(str_h), "missing_strikes": missing_strike, "n_settle": len(settle)}


def updown_frame(root: Path, transport, *, rules_sha: str, blob_get: BlobGet, smoke_path: Path = SMOKE_DEFAULT, exclusion_keys_path: Path = EXCLUSION_KEYS_DEFAULT,
                 require_smoke: bool = True, rps: float = 2.0, disk_cap: int = int(FRAME_OUTPUT_CAP_GB * 1024**3), budget_min: float | None = None,
                 data_dumps: Path | None = None, data_dumps_cap_gb: float = cm.DATA_DUMPS_FETCH_CAP_GB, wall_clock: Callable[[], float] = time.time,
                 sleep=time.sleep, live_check=None, health_check=None, snapshot_root: Path | None = None, should_stop: Callable[[], bool] | None = None,
                 now: float | None = None, pacer: Pacer | None = None, run_id: str = RUN_FRAME, id_sources: dict[str, set[str]] | None = None,
                 prior_archives_meta: dict | None = None) -> dict:
    """One resumable chunk of q0165. Refusals first (run id, root, smoke b and c, exclusion files), headroom (exit 75), sticky end states, the Gamma frame
    walk (per day), the id / key drop and the week split (``frame.csv.gz`` and ``split.json`` are written before the first Binance request), the
    verified Binance archives, then the feature / strike / guarded files."""
    root = Path(root)
    cm.refuse_run_id(run_id, RUN_FRAME)
    cm.refuse_path(root)
    if require_smoke:
        smoke_ok(smoke_path, rules_sha, ("b", "c"))
    ids, ksets, krep, ksha = _read_exclusion(Path(exclusion_keys_path))
    rdir = root / run_id
    term = cm.prior_terminal(rdir)
    if term:
        return term
    mp = rdir / "manifest.json"
    prior = json.loads(mp.read_text()) if mp.exists() else {}
    if prior.get("complete") is True and prior.get("stopped") is None:
        return {"stopped": None, "status": FRAME_COMPLETE, "complete": True, "counts": prior.get("counts")}
    if prior.get("status") in (UNVERIFIED, SOURCE_UNVERIFIED):
        return {"stopped": prior["status"], "status": prior["status"], "complete": False}
    cm.require_room(data_dumps, data_dumps_cap_gb, disk_cap)
    days = b_days()
    fr = cm.open_run(root, run_id, transport, allowed_run_id=RUN_FRAME, kind="cb8_updown_frame", label="CB8-B frame", params={"days": [days[0], days[-1], len(days)],
                     "evidence_role": "exploratory_historical"}, rules_sha=rules_sha, key_fp="", disk_cap=disk_cap, rps=rps, budget_min=budget_min, now=now,
                     sleep=sleep, live_check=live_check, wall_clock=wall_clock, snapshot_root=snapshot_root, health_check=health_check)
    fr.extra_state["exclusion_keys_sha256"] = ksha
    why = fr.unhealthy()
    if why:
        m = fr.manifest(why, {"transient": True})
        m["status"] = "in_progress"
        return m
    pacer = pacer or Pacer(min(rps, BINANCE_RPS), sleep)
    split_p = rdir / "split.json"
    try:
        if not split_p.exists():
            stopped = walk_frame(fr, days, should_stop)
            if stopped:
                m = fr.manifest(stopped, {"transient": True})
                m["status"] = "in_progress"
                return m
            if krep.get("disjointness") == UNVERIFIED:
                (rdir / "DISJOINTNESS_UNVERIFIED.json").write_text(json.dumps({"run_id": run_id, "exclusion_report": krep, "rule": "design 1.3: > 2% of exclusion ids without metadata -> B1 not testable (p = 1, counted)"}, indent=1, sort_keys=True))
                m = fr.manifest(UNVERIFIED, {"status": UNVERIFIED})
                m["status"] = UNVERIFIED
                return m
            recs = list(c6.iter_partial(rdir / "frame_partial_guarded.jsonl.gz"))
            rows = [r for rec in recs for r in rec["rows"]]
            kept, rep = drop_and_split(rows, ids, ksets, id_sources=id_sources)
            rep["frame_walk"] = {"days_walked": len(recs), "n_raw": sum(rec["n_raw"] for rec in recs), "capped_days": sum(1 for rec in recs if rec["capped"]),
                                 "rejected": {}}
            for rec in recs:
                for k, v in rec["reasons"].items():
                    rep["frame_walk"]["rejected"][k] = rep["frame_walk"]["rejected"].get(k, 0) + v
            walked = {rec["day"] for rec in recs}
            failed_days = sorted(set(days) - walked)  # the Gamma request for the day failed 3 times: a source failure, not a day without a market
            days_missing = sorted(walked - {r["day"] for r in kept})  # walked, request succeeded, no kept market
            rep["frame_request_failed_days"] = len(failed_days)
            rep["frame_request_failed_day_list"] = failed_days
            rep["days_without_market"] = len(days_missing)
            fr.budget.write_gz_csv(rdir / "frame.csv.gz", FRAME_COLUMNS, ([r.get(c, "") for c in FRAME_COLUMNS] for r in sorted(kept, key=lambda x: (x["day"], x["asset"]))))
            fr.budget.write(split_p, json.dumps({"seed": SEED_SPLIT, "week_table": {str(k): v for k, v in sorted(week_split().items())}, "report": rep,
                                                 "days": {d: day_split(d) for d in days}}, indent=1, sort_keys=True, default=float).encode())  # last: marks the stage
            fr.counts.update(n_markets=len(kept), n_screen=rep["by_split"]["screen"], n_holdout=rep["by_split"]["holdout"])
        stopped = binance_fetch(fr, blob_get, pacer, should_stop)
        if stopped == SOURCE_UNVERIFIED:
            (rdir / "SOURCE_UNVERIFIED.json").write_text(json.dumps({"run_id": run_id, "rule": "Binance archive checksum mismatch or missing after 3 attempts -> B 'not run (source)'"}, indent=1))
            m = fr.manifest(SOURCE_UNVERIFIED, {"status": SOURCE_UNVERIFIED})
            m["status"] = SOURCE_UNVERIFIED
            return m
        if stopped:
            m = fr.manifest(stopped, {"transient": True})
            m["status"] = "in_progress"
            return m
        counts = finalize_frame(fr, rdir, days)
        fr.counts.update(counts)
        fr.extra_state["archives_vs_prior_run"] = compare_archive_meta(prior_archives_meta, fr.extra_state["archives"])
    except OSError as exc:
        return cm.disk_budget_end(fr, exc)
    m = fr.manifest(None, {"complete": True, "status": FRAME_COMPLETE})
    m["status"] = FRAME_COMPLETE
    return m
