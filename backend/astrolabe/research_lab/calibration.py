"""Development study C1: are Polymarket prices calibrated as probabilities?

DEVELOPMENT/retrospective only. Pure functions (sampling, outcome parsing, point-in-time price
lookup, reliability tables, calibration regression, clustered bootstrap) plus a small polite HTTP
fetcher. Nothing here is prospective evidence, an edge claim or a trading signal. The design is
registered in ``docs/research_lab/EXPERIMENT_LEDGER.md`` (study C1) before any data is fetched.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from typing import Any

import httpx
import numpy as np

SEED = "C1-2026-10-11-a41f"
BOOT_SEED = 117
WINDOW_START = datetime(2026, 7, 13, tzinfo=UTC)
WINDOW_END = datetime(2026, 10, 4, tzinfo=UTC)
BLOCK_HOURS = 6
N_PERIODS = 3
BLOCKS_PER_PERIOD = 12
VOLUME_BANDS = (100.0, 1e3, 1e4, 1e5, math.inf)
PER_CELL = 250
LEADS = {"1d": 86400, "7d": 7 * 86400, "30d": 30 * 86400}
MAX_AGE = 6 * 3600
FETCH_WINDOW = 6 * 3600
FIDELITY = 10
CLIP = 0.001
BIN_EDGES = (0, 0.02, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.98, 1.0)
GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
UA = "Astrolabe/0.1 (research; read-only)"
RESOLVED_HI = 0.999
RESOLVED_LO = 0.001


# ---------------------------------------------------------------- parsing


def parse_ts(value: Any) -> float | None:
    """Parse Gamma timestamps ('2026-09-02 03:37:28+00', ISO with Z) to epoch seconds."""
    if not value or not isinstance(value, str):
        return None
    s = value.strip().replace(" ", "T")
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    if re.search(r"[+-]\d{2}$", s) and "T" in s:
        s += ":00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.timestamp()


def _json_list(value: Any) -> list | None:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            out = json.loads(value)
        except ValueError:
            return None
        return out if isinstance(out, list) else None
    return None


def parse_outcome(market: dict) -> tuple[int | None, str]:
    """Return (y, reason). y=1 iff outcome 0 won; None with an exclusion reason otherwise."""
    if market.get("umaResolutionStatus") != "resolved":
        return None, "not_resolved"
    prices = _json_list(market.get("outcomePrices"))
    if not prices or len(prices) != 2:
        return None, "bad_prices"
    try:
        p0, p1 = float(prices[0]), float(prices[1])
    except (TypeError, ValueError):
        return None, "bad_prices"
    if p0 >= RESOLVED_HI and p1 <= RESOLVED_LO:
        return 1, "ok"
    if p1 >= RESOLVED_HI and p0 <= RESOLVED_LO:
        return 0, "ok"
    if abs(p0 - 0.5) <= RESOLVED_LO and abs(p1 - 0.5) <= RESOLVED_LO:
        return None, "split_50_50"
    return None, "other_price_vector"


CATEGORY_RULES = (
    ("sports", {"sports", "nfl", "nba", "mlb", "nhl", "soccer", "tennis", "football", "mma",
                "ufc", "golf", "cricket", "esports", "baseball", "basketball", "hockey"}),
    ("crypto", {"crypto", "bitcoin", "ethereum", "solana", "xrp", "crypto-prices"}),
    ("politics", {"politics", "elections", "us-politics", "primaries", "trump",
                  "global-elections"}),
    ("geopolitics", {"geopolitics", "world", "world-affairs", "middle-east", "ukraine", "war"}),
    ("economy", {"economy", "finance", "business", "fed", "stocks", "economic-policy", "inflation",
                 "commodities", "earnings"}),
    ("tech", {"tech", "ai", "technology", "openai"}),
    ("culture", {"culture", "pop-culture", "entertainment", "music", "movies", "tv", "awards",
                 "celebrities", "social-media"}),
    ("science_weather", {"science", "weather", "climate", "space", "health"}),
)


def coarse_category(tag_slugs: Iterable[str]) -> str:
    tags = {str(t).lower() for t in tag_slugs}
    for name, members in CATEGORY_RULES:
        if tags & members:
            return name
    return "other"


def compact_market(m: dict) -> dict | None:
    """Reduce a raw Gamma market to the fields the study needs; None if not binary."""
    outcomes = _json_list(m.get("outcomes"))
    tokens = _json_list(m.get("clobTokenIds"))
    if not outcomes or not tokens or len(outcomes) != 2 or len(tokens) != 2:
        return None
    events = m.get("events") or []
    tags = [t.get("slug") for t in (m.get("tags") or []) if isinstance(t, dict) and t.get("slug")]
    try:
        volume = float(m.get("volumeNum") if m.get("volumeNum") is not None else m.get("volume"))
    except (TypeError, ValueError):
        volume = 0.0
    return {
        "market_id": str(m.get("id")),
        "condition_id": m.get("conditionId"),
        "event_id": str(events[0].get("id")) if events and events[0].get("id") else None,
        "token0": str(tokens[0]),
        "outcome0": str(outcomes[0]),
        "outcome1": str(outcomes[1]),
        "volume": volume,
        "start_ts": parse_ts(m.get("startDate")),
        "end_ts": parse_ts(m.get("endDate")),
        "closed_ts": parse_ts(m.get("closedTime")),
        "uma_status": m.get("umaResolutionStatus"),
        "outcome_prices": m.get("outcomePrices"),
        "tags": tags[:12],
        "category": coarse_category(tags),
        "question": (m.get("question") or "")[:120],
    }


# ---------------------------------------------------------------- sampling


def _rng(label: str) -> np.random.Generator:
    digest = hashlib.sha256(f"{SEED}|{label}".encode()).digest()
    return np.random.default_rng(int.from_bytes(digest[:8], "big"))


def make_blocks(start: datetime = WINDOW_START, end: datetime = WINDOW_END,
                hours: int = BLOCK_HOURS) -> list[tuple[float, float]]:
    step = hours * 3600
    t0, t1 = start.timestamp(), end.timestamp()
    n = int((t1 - t0) // step)
    return [(t0 + i * step, t0 + (i + 1) * step) for i in range(n)]


def draw_blocks(n_blocks: int, periods: int = N_PERIODS,
                per_period: int = BLOCKS_PER_PERIOD) -> list[dict]:
    """Stratified SRS of block indices; returns [{index, period, pi_block}] sorted by index."""
    out: list[dict] = []
    for k, chunk in enumerate(np.array_split(np.arange(n_blocks), periods)):
        take = min(per_period, len(chunk))
        pick = _rng(f"blocks|{k}").choice(chunk, size=take, replace=False)
        out += [{"index": int(i), "period": k, "pi_block": take / len(chunk)} for i in pick]
    return sorted(out, key=lambda r: r["index"])


def volume_band(volume: float, bands: tuple[float, ...] = VOLUME_BANDS) -> int | None:
    for i in range(len(bands) - 1):
        if bands[i] <= volume < bands[i + 1]:
            return i
    return None


def draw_stage2(frame: list[dict], per_cell: int = PER_CELL) -> list[dict]:
    """Stratified draw by (period, volume band). Uses only frame fields, never outcomes.

    Each frame row needs ``market_id``, ``period``, ``pi_block`` and ``volume``. Returns the
    sampled rows with ``band``, ``n_cell``, ``N_cell``, ``pi`` and ``weight`` (1/pi) added.
    """
    cells: dict[tuple[int, int], list[dict]] = {}
    for row in frame:
        band = volume_band(row["volume"])
        if band is None:
            continue
        cells.setdefault((row["period"], band), []).append(row)
    out: list[dict] = []
    for key in sorted(cells):
        rows = sorted(cells[key], key=lambda r: r["market_id"])
        n = min(per_cell, len(rows))
        idx = _rng(f"cell|{key[0]}|{key[1]}").choice(len(rows), size=n, replace=False)
        for i in sorted(int(j) for j in idx):
            r = dict(rows[i])
            pi = r["pi_block"] * n / len(rows)
            r.update({"band": key[1], "n_cell": n, "N_cell": len(rows), "pi": pi,
                      "weight": 1.0 / pi})
            out.append(r)
    return out


# ---------------------------------------------------------------- point-in-time prices


def anchor_ts(end_ts: float | None, closed_ts: float | None) -> float | None:
    """Primary anchor T = min(endDate, closedTime); either alone if the other is missing."""
    vals = [v for v in (end_ts, closed_ts) if v is not None]
    return min(vals) if vals else None


def point_in_time_price(history: list[dict], at_ts: float,
                        max_age: float = MAX_AGE) -> tuple[float | None, float | None, str]:
    """Last price with t <= at_ts (never a later one). Returns (price, age_seconds, reason)."""
    best: tuple[float, float] | None = None
    for pt in history:
        try:
            t, p = float(pt["t"]), float(pt["p"])
        except (KeyError, TypeError, ValueError):
            continue
        if t <= at_ts and 0.0 <= p <= 1.0 and (best is None or t > best[0]):
            best = (t, p)
    if best is None:
        return None, None, "empty"
    age = at_ts - best[0]
    if age > max_age:
        return None, age, "stale"
    return best[1], age, "ok"


# ---------------------------------------------------------------- statistics


def wilson(k: float, n: float, z: float = 1.959964) -> tuple[float, float]:
    if n <= 0:
        return float("nan"), float("nan")
    ph = k / n
    den = 1 + z * z / n
    centre = (ph + z * z / (2 * n)) / den
    half = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / den
    return max(0.0, centre - half), min(1.0, centre + half)


def reliability(p: np.ndarray, y: np.ndarray, w: np.ndarray,
                edges: tuple[float, ...] = BIN_EDGES) -> list[dict]:
    """Weighted binned predicted vs realised with Wilson CIs on the effective sample size."""
    rows = []
    last = len(edges) - 2
    for i in range(len(edges) - 1):
        hi_ok = (p <= edges[i + 1]) if i == last else (p < edges[i + 1])
        m = (p >= edges[i]) & hi_ok
        n = int(m.sum())
        if n == 0:
            rows.append({"lo": edges[i], "hi": edges[i + 1], "n": 0})
            continue
        ws = w[m]
        sw = float(ws.sum())
        freq = float((ws * y[m]).sum() / sw)
        n_eff = sw * sw / float((ws * ws).sum())
        lo, hi = wilson(freq * n_eff, n_eff)
        rows.append({"lo": edges[i], "hi": edges[i + 1], "n": n, "n_eff": n_eff,
                     "mean_price": float((ws * p[m]).sum() / sw), "freq": freq,
                     "ci_lo": lo, "ci_hi": hi, "gap": freq - float((ws * p[m]).sum() / sw)})
    return rows


def fold_favourite(p: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Favourite view: price of the favoured side and whether that side won (ties: outcome 0)."""
    fav0 = p >= 0.5
    return np.where(fav0, p, 1 - p), np.where(fav0, y, 1 - y)


def logit(p: np.ndarray, clip: float = CLIP) -> np.ndarray:
    q = np.clip(p, clip, 1 - clip)
    return np.log(q / (1 - q))


def fit_logistic(x: np.ndarray, y: np.ndarray, w: np.ndarray,
                 iters: int = 50, ridge: float = 1e-8) -> tuple[float, float]:
    """Weighted logistic y ~ a + b x via Newton/IRLS. Returns (intercept, slope)."""
    X = np.column_stack([np.ones_like(x), x])
    beta = np.array([0.0, 1.0])
    for _ in range(iters):
        eta = np.clip(X @ beta, -30, 30)
        mu = 1 / (1 + np.exp(-eta))
        grad = X.T @ (w * (y - mu)) - ridge * (beta - np.array([0.0, 1.0]))
        hess = (X * (w * mu * (1 - mu))[:, None]).T @ X + ridge * np.eye(2)
        step = np.linalg.solve(hess, grad)
        beta = beta + step
        if np.max(np.abs(step)) < 1e-9:
            break
    return float(beta[0]), float(beta[1])


def scores(p: np.ndarray, y: np.ndarray, w: np.ndarray, clip: float = CLIP) -> dict:
    """Brier / log loss against their perfectly-calibrated expectations, plus slope/intercept."""
    sw = float(w.sum())
    q = np.clip(p, clip, 1 - clip)
    brier = float((w * (p - y) ** 2).sum() / sw)
    brier_cal = float((w * p * (1 - p)).sum() / sw)
    ll = float(-(w * (y * np.log(q) + (1 - y) * np.log(1 - q))).sum() / sw)
    ll_cal = float(-(w * (q * np.log(q) + (1 - q) * np.log(1 - q))).sum() / sw)
    base = float((w * y).sum() / sw)
    brier_clim = base * (1 - base)
    out = {"n": int(len(p)), "base_rate": base, "brier": brier, "brier_if_calibrated": brier_cal,
           "brier_excess": brier - brier_cal, "log_loss": ll, "log_loss_if_calibrated": ll_cal,
           "log_loss_excess": ll - ll_cal, "brier_skill_vs_climatology":
           (1 - brier / brier_clim) if brier_clim > 0 else float("nan")}
    if 0 < base < 1 and len(p) >= 10:
        a, b = fit_logistic(logit(p, clip), y, w)
        eta = a + b * logit(p, clip)
        r = 1 / (1 + np.exp(-eta))
        out.update({"intercept": a, "slope": b,
                    "brier_recalibrated": float((w * (r - y) ** 2).sum() / sw)})
    return out


def cluster_bootstrap(p: np.ndarray, y: np.ndarray, w: np.ndarray, clusters: np.ndarray,
                      stat: Callable[[np.ndarray, np.ndarray, np.ndarray], dict],
                      n_boot: int = 1000, seed: int = BOOT_SEED) -> dict:
    """Percentile CIs for every numeric key of ``stat``, resampling whole clusters.

    Cluster multiplicities multiply the weights, so weighted statistics stay design-consistent.
    """
    _, inv = np.unique(clusters, return_inverse=True)
    k = int(inv.max()) + 1 if len(inv) else 0
    if k < 2:
        return {}
    rng = np.random.default_rng(seed)
    draws: dict[str, list[float]] = {}
    for _ in range(n_boot):
        counts = np.bincount(rng.integers(0, k, size=k), minlength=k)
        wb = w * counts[inv]
        keep = wb > 0
        try:
            res = stat(p[keep], y[keep], wb[keep])
        except (np.linalg.LinAlgError, FloatingPointError):
            continue
        for key, val in res.items():
            if isinstance(val, float) and math.isfinite(val):
                draws.setdefault(key, []).append(val)
    return {key: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]
            for key, v in draws.items() if len(v) >= max(20, n_boot // 2)}


def calibration_report(p: np.ndarray, y: np.ndarray, w: np.ndarray, event_cl: np.ndarray,
                       block_cl: np.ndarray, n_boot: int = 1000) -> dict:
    """Scores with event- and block-clustered CIs and the reliability table (weighted)."""
    keys = ("brier_excess", "log_loss_excess", "intercept", "slope")

    def stat(pp, yy, ww):
        s = scores(pp, yy, ww)
        return {k: s[k] for k in keys if k in s}

    out = {"weighted": scores(p, y, w), "unweighted": scores(p, y, np.ones_like(w)),
           "reliability": reliability(p, y, w)}
    out["ci_event"] = cluster_bootstrap(p, y, w, event_cl, stat, n_boot)
    out["ci_block"] = cluster_bootstrap(p, y, w, block_cl, stat, n_boot)
    fp, fy = fold_favourite(p, y)
    out["favourite_reliability"] = reliability(fp, fy, w, (0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.98,
                                                           1.0))
    return out


# ---------------------------------------------------------------- polite HTTP


class PoliteFetcher:
    """Sequential GET with a fixed delay, backoff on 429/5xx and a back-off on HTML 403."""

    def __init__(self, client: httpx.Client | None = None, delay: float = 0.15,
                 max_requests: int = 40000, sleep: Callable[[float], None] = time.sleep) -> None:
        self.client = client or httpx.Client(headers={"User-Agent": UA}, timeout=60.0)
        self.delay = delay
        self.max_requests = max_requests
        self.sleep = sleep
        self.requests = 0
        self.blocked = 0
        self.errors = 0

    def get_json(self, url: str, params: dict, tries: int = 4) -> tuple[Any, str]:
        """Return (json, 'ok') or (None, reason). Never raises on HTTP errors."""
        for attempt in range(tries):
            if self.requests >= self.max_requests:
                return None, "request_cap"
            self.requests += 1
            self.sleep(self.delay)
            try:
                r = self.client.get(url, params=params)
            except httpx.HTTPError:
                self.errors += 1
                self.sleep(min(2.0 * 2 ** attempt, 30.0))
                continue
            if r.status_code == 200:
                try:
                    return r.json(), "ok"
                except ValueError:
                    return None, "bad_json"
            if r.status_code == 429:
                try:
                    wait = float(r.headers.get("retry-after", ""))
                except ValueError:
                    wait = 2.0 * 2 ** attempt
                self.sleep(min(wait, 60.0))
                continue
            if r.status_code >= 500:
                self.sleep(min(1.0 * 2 ** attempt, 30.0))
                continue
            if r.status_code == 403:
                self.blocked += 1
                self.sleep(30.0 * (attempt + 1))
                continue
            return None, f"http_{r.status_code}"
        return None, "failed_after_retries"


def enumerate_block(fetch: PoliteFetcher, lo_ts: float, hi_ts: float,
                    max_pages: int = 300) -> tuple[list[dict], dict]:
    """All closed binary markets (volume >= 100) with endDate in [lo_ts, hi_ts)."""

    def iso(t: float) -> str:
        return datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    rows: list[dict] = []
    cursor: str | None = None
    limit = 100
    pages = raw = outside = nonbinary = 0
    status = "ok"
    while True:
        if pages >= max_pages:
            status = "page_cap"
            break
        params: dict[str, Any] = {"closed": "true", "limit": limit, "include_tag": "true",
                                  "volume_num_min": int(VOLUME_BANDS[0]),
                                  "end_date_min": iso(lo_ts), "end_date_max": iso(hi_ts)}
        if cursor:
            params["after_cursor"] = cursor
        data, why = fetch.get_json(f"{GAMMA}/markets/keyset", params)
        if data is None and why.startswith(("failed", "http_403")) and limit == 100:
            limit = 99  # ledger-documented detour around a blocked cursor
            continue
        if data is None:
            status = why
            break
        page = data.get("markets") or []
        pages += 1
        raw += len(page)
        for m in page:
            c = compact_market(m)
            if c is None:
                nonbinary += 1
            elif c["end_ts"] is None or not (lo_ts <= c["end_ts"] < hi_ts):
                outside += 1
            else:
                rows.append(c)
        cursor = data.get("next_cursor")
        if not cursor or not page:
            break
    return rows, {"status": status, "pages": pages, "raw": raw, "kept": len(rows),
                  "outside_block": outside, "nonbinary": nonbinary}


def fetch_lead_price(fetch: PoliteFetcher, token: str, lead_ts: float) -> tuple[float | None,
                                                                              float | None, str]:
    params = {"market": token, "startTs": int(lead_ts - FETCH_WINDOW), "endTs": int(lead_ts),
              "fidelity": FIDELITY}
    data, why = fetch.get_json(f"{CLOB}/prices-history", params)
    if data is None:
        return None, None, f"error:{why}"
    hist = data.get("history") if isinstance(data, dict) else None
    if not isinstance(hist, list):
        return None, None, "error:bad_shape"
    return point_in_time_price(hist, lead_ts)
