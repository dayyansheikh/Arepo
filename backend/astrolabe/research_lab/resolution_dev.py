"""Resolution-forecasting development study (target T5). EXPLORATORY, HISTORICAL, DEVELOPMENT ONLY.

Question: does a model on point-in-time market features (price path, momentum, volatility, trade
volume history, listing age, distance from 0/1, category, neg-risk structure) predict the eventual
binary resolution better than the market price alone, and better than a *recalibrated* price
(Platt / isotonic, fitted on earlier markets only), at 1, 3 and 7 days before the scheduled close?

Every output carries ``evidence_role = "exploratory_historical"``. Nothing here is prospective
evidence, a calibration claim, an edge claim or a trading signal. The study is registered in
``docs/research_lab/RESOLUTION_DEV_STUDY.md`` and the experiment ledger.

Design decisions (fixed before any outcome was read):

* **Universe.** Binary Gamma markets, ``closed=true``, lifetime ``volumeNum >= 100`` (API filter,
  as in C1), scheduled ``endDate`` in [2025-10-11, 2026-10-04). Enumerated by 6h ``endDate``
  blocks through ``/markets/keyset``: blocks are a seeded stratified sample (4 periods x
  ``BLOCKS_PER_PERIOD``), every market of a drawn block is enumerated. Frame filter (ex-ante
  field): listed at least 30h before the scheduled end. Stage 2: seeded stratified draw by
  period x coarse category (``PER_CELL`` per cell), using frame fields only; pi and 1/pi kept.
* **Horizon point.** ``t_h = endDate - h`` (the *scheduled* end, known ex ante). ``closedTime``
  is NOT used as the anchor because early closure correlates with the outcome ("by date" markets
  close early on Yes), so anchoring on it, or a time-to-close feature, would leak. A row exists
  at ``t_h`` only if the market was listed (``startDate <= t_h``) and still open
  (``closedTime > t_h``), both observable at ``t_h``.
* **Point in time.** CLOB ``prices-history`` at 10-minute fidelity for [end-14d, end-1d]; the
  stamp convention is not documented, so a point stamped ``s`` is usable at ``t`` only if
  ``s + 600 < t`` (same conservative lag as ``history_backfill``). Trades (Data API) are kept
  only if ``ts < t``; trades after ``end - 1d`` are discarded before storage. Lifetime volume,
  liquidity, ``closedTime`` and outcome fields are never features.
* **Label.** ``calibration.parse_outcome`` (outcome 0 paid out = 1). Not-resolved, 50-50 and other
  price vectors are excluded and counted.
* **Trade coverage.** The trades endpoint reaches at most 20,000 newest trades. A trade window
  not covered is NaN. Because truncation depends on future trading, the primary population is
  markets whose fetched trades cover every trade window (counted); a sensitivity uses all rows
  without trade features.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import math
import time
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import calibration as C

EVIDENCE_ROLE = "exploratory_historical"
LABEL = "DEVELOPMENT / EXPLORATORY_HISTORICAL (retrospective; not prospective evidence)"
SEED = "T5-RESDEV-2026-10-11-7c2e"
BOOT_SEED = 118
WINDOW_START = datetime(2025, 10, 11, tzinfo=UTC)
WINDOW_END = datetime(2026, 10, 4, tzinfo=UTC)
N_PERIODS = 4
BLOCKS_PER_PERIOD = 12
PER_CELL = 250
MIN_LISTED_BEFORE_END = 30 * 3600
HORIZONS = {"1d": 86400, "3d": 3 * 86400, "7d": 7 * 86400}
HISTORY_DAYS = 14
FIDELITY = 10
POINT_LAG = 600
MAX_PRICE_AGE = 6 * 3600
TRADE_PAGE = 10000
TRADE_MAX_PAGES = 2
DATA_TRADES = "https://data-api.polymarket.com/trades"
CLIP = 0.001
EMBARGO = 2 * 86400
N_CHUNKS = 8
FIRST_TEST_CHUNK = 2
CATEGORIES = ("sports", "crypto", "politics", "geopolitics", "economy", "tech", "culture",
              "science_weather", "other")

PRICE_FEATURES = ("dist01", "chg_1h", "chg_6h", "chg_24h", "chg_72h", "lchg_24h", "vol_24h",
                  "vol_72h", "range_24h", "max_7d", "min_7d", "n_moves_24h", "price_age_h")
META_FEATURES = ("age_h", "log_life_h", "end_midnight", "neg_risk", "neg_risk_aug", "yes_no",
                 *(f"cat_{c}" for c in CATEGORIES))
FLOW_FEATURES = ("tf_n_24h", "tf_lnotional_24h", "tf_lnotional_7d", "tf_lnotional_cum",
                 "tf_buy_share_24h", "tf_last_age_h", "tf_ltp_minus_p")
BASE_FEATURE = "logit_p"
ALL_FEATURES = (BASE_FEATURE, *PRICE_FEATURES, *META_FEATURES, *FLOW_FEATURES)
FAMILY_MAP = {"market_state": list(PRICE_FEATURES), "metadata": list(META_FEATURES),
              "flow": list(FLOW_FEATURES)}
FLOW_WINDOW_MAX = 7 * 86400  # longest trade window; tf_lnotional_cum needs full history


# ---------------------------------------------------------------- sampling


def _rng(label: str) -> np.random.Generator:
    digest = hashlib.sha256(f"{SEED}|{label}".encode()).digest()
    return np.random.default_rng(int.from_bytes(digest[:8], "big"))


def draw_blocks(n_blocks: int, periods: int = N_PERIODS,
                per_period: int = BLOCKS_PER_PERIOD) -> list[dict]:
    out: list[dict] = []
    for k, chunk in enumerate(np.array_split(np.arange(n_blocks), periods)):
        take = min(per_period, len(chunk))
        pick = _rng(f"blocks|{k}").choice(chunk, size=take, replace=False)
        out += [{"index": int(i), "period": k, "pi_block": take / len(chunk)} for i in pick]
    return sorted(out, key=lambda r: r["index"])


def frame_row(m: dict) -> dict | None:
    """Compact frame row (C1 fields plus neg-risk / parent structure); None if not binary."""
    c = C.compact_market(m)
    if c is None:
        return None
    ev = (m.get("events") or [{}])[0] or {}
    c.update({
        "neg_risk": bool(m.get("negRisk")),
        "neg_risk_id": m.get("negRiskMarketID") or None,
        "neg_risk_aug": bool(ev.get("negRiskAugmented")),
        "parent": str(ev.get("parentEvent") or ev.get("seriesSlug") or "") or None,
    })
    return c


def frame_eligible(r: dict) -> bool:
    """Ex-ante frame filter: start and end known, listed >= 30h before the scheduled end."""
    return (r["start_ts"] is not None and r["end_ts"] is not None
            and r["start_ts"] <= r["end_ts"] - MIN_LISTED_BEFORE_END)


def draw_by_category(frame: list[dict], per_cell: int = PER_CELL) -> list[dict]:
    """Stratified SRS by (period, category) from frame fields only; adds pi and weight."""
    cells: dict[tuple[int, str], list[dict]] = {}
    for r in frame:
        cells.setdefault((r["period"], r["category"]), []).append(r)
    out: list[dict] = []
    for key in sorted(cells):
        rows = sorted(cells[key], key=lambda r: r["market_id"])
        n = min(per_cell, len(rows))
        idx = _rng(f"cell|{key[0]}|{key[1]}").choice(len(rows), size=n, replace=False)
        for i in sorted(int(j) for j in idx):
            r = dict(rows[i])
            pi = r["pi_block"] * n / len(rows)
            r.update({"n_cell": n, "N_cell": len(rows), "pi": pi, "weight": 1.0 / pi})
            out.append(r)
    return out


# ---------------------------------------------------------------- polite fetching


def in_collector_window(now: float | None = None) -> bool:
    """True during :25-:59 after an even UTC hour (the AREPO collector runs then)."""
    d = datetime.fromtimestamp(time.time() if now is None else now, UTC)
    return d.hour % 2 == 0 and d.minute >= 25


def is_live_pass_command(cmd: str) -> bool:
    """A process *running* ``arepo_pass.sh`` (the script as argv[0] or argv[1]), not a shell or
    watcher whose command line merely mentions it (``pgrep -f`` alone matches those too)."""
    parts = cmd.split()
    return any(p.endswith("arepo_pass.sh") for p in parts[:2])


def live_pass_running() -> bool:
    """True while the live prospective pass (``arepo_pass.sh``) runs; it has priority."""
    import subprocess

    try:
        r = subprocess.run(["ps", "-axo", "command="], capture_output=True, text=True,
                           timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return False
    return any(is_live_pass_command(line) for line in r.stdout.splitlines())


class WindowedFetcher(C.PoliteFetcher):
    """``PoliteFetcher`` that yields to live collection before every request: it waits out the
    collector window (:25-:59 after even UTC hours) and, while ``arepo_pass.sh`` runs, sleeps
    30 s and re-checks. Live prospective data always has priority over this study."""

    live_check: Callable[[], bool] = staticmethod(live_pass_running)

    def get_json(self, url: str, params: dict, tries: int = 4) -> tuple[Any, str]:
        while True:
            if in_collector_window():
                self.sleep(60.0)
            elif self.live_check():
                self.sleep(30.0)
            else:
                break
        return super().get_json(url, params, tries)


def enumerate_block(fetch: C.PoliteFetcher, lo_ts: float, hi_ts: float,
                    max_pages: int = 300) -> tuple[list[dict], dict]:
    """C1's keyset enumeration of one 6h ``endDate`` block, compacted with ``frame_row``."""

    def iso(t: float) -> str:
        return datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    rows: list[dict] = []
    cursor: str | None = None
    pages = raw = outside = nonbinary = 0
    status = "ok"
    while True:
        if pages >= max_pages:
            status = "page_cap"
            break
        params: dict[str, Any] = {"closed": "true", "limit": 100, "include_tag": "true",
                                  "volume_num_min": 100, "end_date_min": iso(lo_ts),
                                  "end_date_max": iso(hi_ts)}
        if cursor:
            params["after_cursor"] = cursor
        data, why = fetch.get_json(f"{C.GAMMA}/markets/keyset", params)
        if data is None:
            status = why
            break
        page = data.get("markets") or []
        pages += 1
        raw += len(page)
        for m in page:
            c = frame_row(m)
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


def price_request(r: dict) -> dict:
    end = r["end_ts"]
    lo = max(r["start_ts"], end - HISTORY_DAYS * 86400)
    return {"market": r["token0"], "startTs": int(lo), "endTs": int(end - HORIZONS["1d"]),
            "fidelity": FIDELITY}


def fetch_prices(fetch: C.PoliteFetcher, r: dict) -> tuple[list[list[float]] | None, str]:
    data, why = fetch.get_json(f"{C.CLOB}/prices-history", price_request(r))
    if data is None:
        return None, f"error:{why}"
    hist = data.get("history") if isinstance(data, dict) else None
    if not isinstance(hist, list):
        return None, "error:bad_shape"
    cutoff = r["end_ts"] - HORIZONS["1d"]
    pts = {}
    for h in hist:
        try:
            t, p = int(h["t"]), float(h["p"])
        except (KeyError, TypeError, ValueError):
            continue
        if t <= cutoff and 0.0 <= p <= 1.0:
            pts[t] = p
    return [[t, p] for t, p in sorted(pts.items())], "ok"


def compact_trades(raw: list[dict], cutoff: float) -> list[list[float]]:
    """[ts, sign, size, price0] for trades with ts < cutoff. sign +1 = buys outcome 0 (BUY of
    token 0 or SELL of token 1); price0 is the outcome-0 price. No wallet is kept."""
    out = []
    for t in raw:
        try:
            ts, side = int(t["timestamp"]), str(t["side"]).upper()
            size, price, idx = float(t["size"]), float(t["price"]), int(t["outcomeIndex"])
        except (KeyError, TypeError, ValueError):
            continue
        if ts >= cutoff:
            continue
        sign = 1 if (side == "BUY") == (idx == 0) else -1
        out.append([ts, sign, size, price if idx == 0 else 1.0 - price])
    out.sort(key=lambda x: x[0])
    return out


def fetch_trades(fetch: C.PoliteFetcher, r: dict) -> tuple[dict | None, str]:
    """Newest-first trades (<= 2 pages of 10,000). ``covered_from`` = oldest fetched trade time if
    the pages were exhausted while still full (older trades unreachable), else None."""
    raw: list[dict] = []
    truncated = False
    for page in range(TRADE_MAX_PAGES):
        data, why = fetch.get_json(DATA_TRADES, {"market": r["condition_id"], "limit": TRADE_PAGE,
                                                 "offset": page * TRADE_PAGE})
        if data is None or not isinstance(data, list):
            return None, f"error:{why}"
        raw += data
        if len(data) < TRADE_PAGE:
            break
    else:
        truncated = True
    oldest = min((int(t["timestamp"]) for t in raw if "timestamp" in t), default=None)
    trades = compact_trades(raw, r["end_ts"] - HORIZONS["1d"])
    return {"trades": trades, "n_raw": len(raw), "truncated": truncated,
            "covered_from": oldest if truncated else None}, "ok"


# ---------------------------------------------------------------- point-in-time features


def logit(p: np.ndarray | float, clip: float = CLIP):
    q = np.clip(p, clip, 1 - clip)
    return np.log(q / (1 - q))


def _asof(ts: np.ndarray, ps: np.ndarray, t: float, max_age: float = MAX_PRICE_AGE
          ) -> tuple[float, float]:
    """Last point usable strictly before ``t`` (stamp + POINT_LAG < t) and its age."""
    i = int(np.searchsorted(ts + POINT_LAG, t, side="left")) - 1
    if i < 0:
        return math.nan, math.nan
    age = t - ts[i]
    if age > max_age:
        return math.nan, age
    return float(ps[i]), float(age)


def _window(ts: np.ndarray, ps: np.ndarray, t: float, secs: float) -> np.ndarray:
    lo = np.searchsorted(ts + POINT_LAG, t - secs, side="left")
    hi = np.searchsorted(ts + POINT_LAG, t, side="left")
    return ps[lo:hi]


def price_features(ts: np.ndarray, ps: np.ndarray, t: float) -> dict:
    p, age = _asof(ts, ps, t)
    out = {"p": p, BASE_FEATURE: float(logit(p)) if p == p else math.nan,
           "dist01": min(p, 1 - p) if p == p else math.nan,
           "price_age_h": age / 3600 if age == age else math.nan}
    for tag, secs in (("1h", 3600), ("6h", 6 * 3600), ("24h", 86400), ("72h", 3 * 86400)):
        q, _ = _asof(ts, ps, t - secs)
        out[f"chg_{tag}"] = p - q if p == p and q == q else math.nan
        if tag == "24h":
            out["lchg_24h"] = float(logit(p) - logit(q)) if p == p and q == q else math.nan
    for tag, secs in (("24h", 86400), ("72h", 3 * 86400)):
        w = _window(ts, ps, t, secs)
        # A window counts only if the series reaches back at least 90% of its length.
        full = len(ts) and (t - POINT_LAG - ts[0]) >= 0.9 * secs
        d = np.diff(logit(w)) if len(w) >= 3 else np.array([])
        out[f"vol_{tag}"] = float(np.std(d)) if full and len(d) >= 2 else math.nan
        if tag == "24h":
            out["range_24h"] = float(w.max() - w.min()) if full and len(w) else math.nan
            out["n_moves_24h"] = float((np.abs(np.diff(w)) > 1e-9).sum()) if full and len(w) > 1 \
                else math.nan
    w7 = _window(ts, ps, t, 7 * 86400)
    out["max_7d"] = float(w7.max()) if len(w7) else math.nan
    out["min_7d"] = float(w7.min()) if len(w7) else math.nan
    return out


def flow_features(tr: np.ndarray | None, covered_from: float | None, t: float, p: float) -> dict:
    """Trade-history features from trades with ts < t. A window that starts before
    ``covered_from`` (older trades unreachable) is NaN, never 0."""
    out = {k: math.nan for k in FLOW_FEATURES}
    if tr is None:
        return out
    if len(tr) == 0:
        tr = np.zeros((0, 4))
    ts = tr[:, 0]
    hi = int(np.searchsorted(ts, t, side="left"))
    cov = -math.inf if covered_from is None else covered_from

    def win(secs: float) -> tuple[int, bool]:
        return int(np.searchsorted(ts, t - secs, side="left")), (t - secs) >= cov

    notional = tr[:, 2] * tr[:, 3]
    lo24, ok24 = win(86400)
    lo7, ok7 = win(7 * 86400)
    if ok24:
        sz = tr[lo24:hi, 2]
        out["tf_n_24h"] = float(hi - lo24)
        out["tf_lnotional_24h"] = float(np.log1p(notional[lo24:hi].sum()))
        tot = sz.sum()
        out["tf_buy_share_24h"] = float(sz[tr[lo24:hi, 1] > 0].sum() / tot) if tot > 0 else math.nan
    if ok7:
        out["tf_lnotional_7d"] = float(np.log1p(notional[lo7:hi].sum()))
    if covered_from is None:
        out["tf_lnotional_cum"] = float(np.log1p(notional[:hi].sum()))
    if hi > 0 and ts[hi - 1] >= cov:
        out["tf_last_age_h"] = (t - ts[hi - 1]) / 3600
        out["tf_ltp_minus_p"] = float(tr[hi - 1, 3] - p) if p == p else math.nan
    elif covered_from is None:
        out["tf_last_age_h"] = math.nan  # never traded before t
    return out


def flow_covered(covered_from: float | None, t: float) -> bool:
    return covered_from is None or (t - FLOW_WINDOW_MAX) >= covered_from


def meta_features(r: dict, t: float) -> dict:
    end = r["end_ts"]
    out = {"age_h": (t - r["start_ts"]) / 3600,
           "log_life_h": math.log1p(max(end - r["start_ts"], 0) / 3600),
           "end_midnight": float(datetime.fromtimestamp(end, UTC).strftime("%H:%M") == "00:00"),
           "neg_risk": float(bool(r.get("neg_risk"))),
           "neg_risk_aug": float(bool(r.get("neg_risk_aug"))),
           "yes_no": float((r.get("outcome0"), r.get("outcome1")) == ("Yes", "No"))}
    for c in CATEGORIES:
        out[f"cat_{c}"] = float(r.get("category") == c)
    return out


def horizon_status(r: dict, h_secs: int) -> str:
    t = r["end_ts"] - h_secs
    if r["start_ts"] > t:
        return "not_listed"
    if r.get("closed_ts") is not None and r["closed_ts"] <= t:
        return "closed_before"
    return "open"


def market_rows(r: dict, prices: list | None, trades: dict | None) -> tuple[list[dict], Counter]:
    """One feature row per horizon at which the market is open and has a fresh price."""
    rows, st = [], Counter()
    pa = np.asarray(prices or [], float).reshape(-1, 2)
    ts, ps = pa[:, 0], pa[:, 1]
    tr = None if trades is None else np.asarray(trades["trades"], float).reshape(-1, 4)
    cov = None if trades is None else trades.get("covered_from")
    for name, secs in HORIZONS.items():
        status = horizon_status(r, secs)
        if status != "open":
            st[f"{name}:{status}"] += 1
            continue
        t = r["end_ts"] - secs
        f = price_features(ts, ps, t)
        if f["p"] != f["p"]:
            st[f"{name}:no_price"] += 1
            continue
        st[f"{name}:ok"] += 1
        row = {"market_id": r["market_id"], "horizon": name, "t": t, "y": r["y"],
               "end_ts": r["end_ts"], "closed_ts": r.get("closed_ts"),
               "label_ts": max(x for x in (r["end_ts"], r.get("closed_ts")) if x is not None),
               "category": r["category"], "period": r["period"], "block": r["block"],
               "weight": r["weight"], "event": r.get("event_id") or f"m{r['market_id']}",
               "trades_ok": trades is not None, "flow_covered": trades is not None
               and flow_covered(cov, t), **f, **meta_features(r, t)}
        row["dep_group"] = r.get("neg_risk_id") or row["event"]
        row["parent"] = r.get("parent") or row["dep_group"]
        row.update(flow_features(tr, cov, t, f["p"]))
        rows.append(row)
    return rows, st


# ---------------------------------------------------------------- walk-forward folds


@dataclass
class WFold:
    fold_id: str
    train_pos: np.ndarray
    test_pos: np.ndarray


def walk_forward(df: pd.DataFrame, n_chunks: int = N_CHUNKS, first_test: int = FIRST_TEST_CHUNK,
                 embargo: float = EMBARGO) -> list[WFold]:
    """Contiguous chunks by scheduled end; expanding training window. A training row is used only
    if its label time (max(end, closed)) plus ``embargo`` precedes the earliest test origin."""
    order = np.argsort(df["end_ts"].to_numpy(), kind="stable")
    chunks = np.array_split(order, n_chunks)
    label = df["label_ts"].to_numpy(float)
    t = df["t"].to_numpy(float)
    folds = []
    for k in range(first_test, n_chunks):
        test = np.sort(chunks[k])
        if not len(test):
            continue
        cand = np.sort(np.concatenate(chunks[:k]))
        train = cand[label[cand] + embargo < t[test].min()]
        folds.append(WFold(str(k), train, test))
    return folds


def inner_split(df: pd.DataFrame, train_pos: np.ndarray, frac: float = 0.25,
                embargo: float = EMBARGO) -> tuple[np.ndarray, np.ndarray]:
    """Last ``frac`` of the training rows by end is validation; earlier rows (purged) fit."""
    pos = train_pos[np.argsort(df["end_ts"].to_numpy()[train_pos], kind="stable")]
    cut = int(len(pos) * (1 - frac))
    val = pos[cut:]
    fit = pos[:cut]
    if len(val):
        first_val = df["t"].to_numpy(float)[val].min()
        fit = fit[df["label_ts"].to_numpy(float)[fit] + embargo < first_val]
    return fit, val


# ---------------------------------------------------------------- arms


def ll_rows(p: np.ndarray, y: np.ndarray) -> np.ndarray:
    q = np.clip(p, CLIP, 1 - CLIP)
    return -(y * np.log(q) + (1 - y) * np.log(1 - q))


def brier_rows(p: np.ndarray, y: np.ndarray) -> np.ndarray:
    return (np.clip(p, CLIP, 1 - CLIP) - y) ** 2


def _sigmoid(z):
    return 1 / (1 + np.exp(-np.clip(z, -30, 30)))


def fit_platt(p: np.ndarray, y: np.ndarray) -> Callable[[np.ndarray], np.ndarray]:
    a, b = C.fit_logistic(logit(p), y.astype(float), np.ones(len(y)))
    return lambda q: _sigmoid(a + b * logit(q))


def fit_isotonic(p: np.ndarray, y: np.ndarray) -> Callable[[np.ndarray], np.ndarray]:
    from sklearn.isotonic import IsotonicRegression

    iso = IsotonicRegression(y_min=CLIP, y_max=1 - CLIP, out_of_bounds="clip")
    iso.fit(p, y)
    return lambda q: iso.predict(q)


class _Design:
    """Median imputation + missing indicators + standardisation, fitted on training rows."""

    def __init__(self, x: np.ndarray):
        self.med = np.nan_to_num(np.nanmedian(np.where(np.isfinite(x), x, np.nan), axis=0))
        self.miss_cols = np.flatnonzero(np.isnan(x).any(axis=0))
        z = self._raw(x)
        self.mu, self.sd = z.mean(axis=0), z.std(axis=0)
        self.sd[self.sd < 1e-12] = 1.0

    def _raw(self, x):
        m = np.isnan(x)
        z = np.where(m, self.med, x)
        return np.column_stack([z, m[:, self.miss_cols].astype(float)])

    def __call__(self, x):
        return (self._raw(x) - self.mu) / self.sd


ENET_GRID = tuple({"C": c, "l1_ratio": r} for c in (0.01, 0.05, 0.2, 1.0) for r in (0.1, 0.5, 0.9))


def _enet(cfg):
    from sklearn.linear_model import LogisticRegression

    return LogisticRegression(solver="saga", C=cfg["C"],
                              l1_ratio=cfg["l1_ratio"], max_iter=3000, tol=1e-4)


def fit_enet(x_fit, y_fit, x_val, y_val, x_train, y_train) -> tuple[Callable, dict]:
    import warnings

    from sklearn.exceptions import ConvergenceWarning

    best = None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        d = _Design(x_fit)
        for cfg in ENET_GRID:
            m = _enet(cfg).fit(d(x_fit), y_fit)
            loss = ll_rows(m.predict_proba(d(x_val))[:, 1], y_val).mean()
            if best is None or loss < best[0]:
                best = (loss, cfg)
        d = _Design(x_train)
        m = _enet(best[1]).fit(d(x_train), y_train)
    return (lambda x: m.predict_proba(d(x))[:, 1]), {**best[1], "val_ll": float(best[0])}


LGB_N_CONFIGS = 12
LGB_MAX_ROUNDS = 600


def lgb_configs(n: int = LGB_N_CONFIGS) -> list[dict]:
    rng = _rng("lgb_grid")
    space = {"num_leaves": (4, 8, 16), "min_data_in_leaf": (40, 100, 200),
             "lambda_l2": (1.0, 10.0, 50.0), "feature_fraction": (0.6, 0.8, 1.0),
             "learning_rate": (0.02, 0.05)}
    return [{k: v[int(rng.integers(len(v)))] for k, v in space.items()} for _ in range(n)]


def _lgb_params(cfg: dict) -> dict:
    return {"objective": "binary", "seed": 116, "deterministic": True, "force_row_wise": True,
            "num_threads": 1, "verbose": -1, "bagging_fraction": 1.0, **cfg}


def fit_lgbm(x_fit, y_fit, x_val, y_val, x_train, y_train, base_col: int
             ) -> tuple[Callable, dict]:
    """LightGBM boosted from the market prior (init score = logit p). Config and round count are
    chosen on the inner validation split only, then refit on the whole training fold."""
    import lightgbm as lgb

    best = None
    for cfg in lgb_configs():
        dtr = lgb.Dataset(x_fit, y_fit, init_score=x_fit[:, base_col], free_raw_data=False)
        dva = lgb.Dataset(x_val, y_val, init_score=x_val[:, base_col], reference=dtr)
        b = lgb.train(_lgb_params(cfg), dtr, LGB_MAX_ROUNDS, valid_sets=[dva],
                      callbacks=[lgb.early_stopping(30, verbose=False)])
        it = max(int(b.best_iteration or 0), 1)
        raw = b.predict(x_val, num_iteration=it, raw_score=True) + x_val[:, base_col]
        loss = ll_rows(_sigmoid(raw), y_val).mean()
        if best is None or loss < best[0]:
            best = (loss, cfg, it)
    _, cfg, it = best
    b = lgb.train(_lgb_params(cfg), lgb.Dataset(x_train, y_train, init_score=x_train[:, base_col]),
                  it)
    return (lambda x: _sigmoid(b.predict(x, raw_score=True) + x[:, base_col])), {
        **cfg, "rounds": it, "val_ll": float(best[0])}


ARMS = ("price", "platt", "isotonic", "enet", "lgbm")


def run_arms(df: pd.DataFrame, folds: Sequence[WFold], features: Sequence[str],
             arms: Sequence[str] = ARMS) -> tuple[pd.DataFrame, list[dict]]:
    """Out-of-fold predictions per arm (NaN outside test blocks) and per-fold tuning logs."""
    y = df["y"].to_numpy(float)
    p = df["p"].to_numpy(float)
    x = df[list(features)].to_numpy(float)
    base_col = list(features).index(BASE_FEATURE)
    pred = pd.DataFrame(np.nan, index=df.index, columns=list(arms))
    logs = []
    for f in folds:
        tr, te = f.train_pos, f.test_pos
        info: dict = {"fold": f.fold_id, "n_train": len(tr), "n_test": len(te)}
        if len(tr) < 200 or len(np.unique(y[tr])) < 2:
            info["skipped"] = "too_few_training_rows"
            logs.append(info)
            continue
        fit, val = inner_split(df, tr)
        info.update({"n_inner_fit": len(fit), "n_inner_val": len(val)})
        for arm in arms:
            if arm == "price":
                out = p[te]
            elif arm == "platt":
                out = fit_platt(p[tr], y[tr])(p[te])
            elif arm == "isotonic":
                out = fit_isotonic(p[tr], y[tr])(p[te])
            elif arm == "enet":
                fn, info["enet"] = fit_enet(x[fit], y[fit], x[val], y[val], x[tr], y[tr])
                out = fn(x[te])
            elif arm == "lgbm":
                fn, info["lgbm"] = fit_lgbm(x[fit], y[fit], x[val], y[val], x[tr], y[tr], base_col)
                out = fn(x[te])
            else:
                raise ValueError(arm)
            pred.iloc[te, pred.columns.get_loc(arm)] = np.clip(out, CLIP, 1 - CLIP)
        logs.append(info)
    return pred, logs


# ---------------------------------------------------------------- inference


def weighted_cluster_boot(d: np.ndarray, w: np.ndarray, cluster: np.ndarray,
                          n_boot: int = 1000, seed: int = BOOT_SEED) -> dict:
    """Percentile CI of the (weighted) mean of ``d`` resampling whole clusters."""
    ok = np.isfinite(d)
    d, w, cl = d[ok], w[ok], np.asarray(cluster)[ok]
    if len(d) == 0:
        return {"mean": None, "ci": [None, None], "p_pos": None, "n_rows": 0, "n_clusters": 0}
    codes, uniq = pd.factorize(cl)
    k = len(uniq)
    s = np.bincount(codes, weights=w * d, minlength=k)
    sw = np.bincount(codes, weights=w, minlength=k)
    rng = np.random.default_rng(seed)
    means = np.empty(n_boot)
    for i in range(n_boot):
        c = np.bincount(rng.integers(0, k, size=k), minlength=k)
        means[i] = (c * s).sum() / (c * sw).sum()
    lo, hi = np.percentile(means, [2.5, 97.5])
    return {"mean": float((w * d).sum() / w.sum()), "ci": [float(lo), float(hi)],
            "p_pos": float(max((means <= 0).mean(), 1 / (n_boot + 1))),
            "n_rows": int(len(d)), "n_clusters": int(k)}


CLUSTERS = ("event", "dep_group", "parent")


def compare_arms(df: pd.DataFrame, pred: pd.DataFrame, weighted: bool = False,
                 n_boot: int = 1000, mask: np.ndarray | None = None) -> dict:
    """Mean log loss / Brier per arm and paired improvements (baseline loss minus arm loss;
    positive = arm better) vs price, Platt and isotonic, with the conservative hull over the
    event, dep_group and parent clusterings."""
    from .ml_explain import conservative

    ok = pred.notna().all(axis=1).to_numpy()
    if mask is not None:
        ok &= mask
    d = df[ok]
    pr = pred[ok]
    y = d["y"].to_numpy(float)
    w = d["weight"].to_numpy(float) if weighted else np.ones(len(d))
    out: dict = {"n_rows": int(ok.sum()), "n_markets": int(d["market_id"].nunique()),
                 "n_events": int(d["event"].nunique()), "arms": {}, "diff": {}}
    if not ok.any():
        return out
    out["base_rate"] = float((w * y).sum() / w.sum())
    ll = {a: ll_rows(pr[a].to_numpy(), y) for a in pr.columns}
    br = {a: brier_rows(pr[a].to_numpy(), y) for a in pr.columns}
    for a in pr.columns:
        q = pr[a].to_numpy()
        ia, sl = C.fit_logistic(logit(q), y, w) if 0 < y.mean() < 1 else (math.nan, math.nan)
        out["arms"][a] = {"log_loss": float((w * ll[a]).sum() / w.sum()),
                          "brier": float((w * br[a]).sum() / w.sum()),
                          "cal_intercept": ia, "cal_slope": sl}
    for base in ("price", "platt", "isotonic"):
        if base not in pr.columns:
            continue
        for a in pr.columns:
            if a == base:
                continue
            res = {}
            for metric, rows in (("log_loss", ll), ("brier", br)):
                diff = rows[base] - rows[a]
                boots = {c: weighted_cluster_boot(diff, w, d[c].to_numpy(), n_boot)
                         for c in CLUSTERS}
                res[metric] = {**boots, "conservative": conservative(boots)}
            out["diff"][f"{a}_vs_{base}"] = res
    return out


def per_fold_signs(df: pd.DataFrame, pred: pd.DataFrame, folds: Sequence[WFold], arm: str,
                   base: str) -> dict:
    y = df["y"].to_numpy(float)
    vals = {}
    for f in folds:
        te = f.test_pos
        a, b = pred[arm].to_numpy()[te], pred[base].to_numpy()[te]
        ok = np.isfinite(a) & np.isfinite(b)
        if ok.any():
            vals[f.fold_id] = float((ll_rows(b[ok], y[te][ok]) - ll_rows(a[ok], y[te][ok])).mean())
    return {"per_fold_dll": vals, "n_positive": sum(v > 0 for v in vals.values()),
            "n_folds": len(vals)}


def hold_to_resolution_descriptive(df: pd.DataFrame, pred: pd.DataFrame, arm: str,
                                   gap: float = 0.05) -> dict:
    """GROSS, NON-EXECUTABLE descriptive: mean payoff of buying the side the model favours over
    the backfill price by > ``gap`` at that price, held to resolution. No spread, no fees, no
    depth; the backfill price is not an executable ask. Never a profitability claim."""
    ok = pred[arm].notna().to_numpy()
    q, p, y = pred[arm].to_numpy()[ok], df["p"].to_numpy()[ok], df["y"].to_numpy(float)[ok]
    ev = df["event"].to_numpy()[ok]
    out = {}
    for side, sel, pay in (("buy_outcome0", q - p > gap, y - p), ("buy_outcome1", p - q > gap,
                                                                  p - y)):
        if sel.sum() == 0:
            out[side] = {"n": 0}
            continue
        b = weighted_cluster_boot(pay[sel], np.ones(int(sel.sum())), ev[sel], 500)
        out[side] = {"n": int(sel.sum()), "mean_gross_payoff_per_share": b["mean"], "ci": b["ci"],
                     "n_events": b["n_clusters"]}
    out["note"] = ("gross, no fees/spread/depth, backfill price not executable; descriptive only")
    return out


# ---------------------------------------------------------------- io helpers


def write_json_gz(path: Path, obj: Any) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(obj, fh)


def read_json_gz(path: Path) -> Any:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def dir_bytes(path: Path) -> int:
    return sum(p.stat().st_size for p in Path(path).rglob("*") if p.is_file())
