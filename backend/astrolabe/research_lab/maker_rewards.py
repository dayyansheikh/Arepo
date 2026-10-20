# ruff: noqa: E501
"""Maker P&L held to resolution, and liquidity-reward yield (prior-art gaps 5 and 6; DEVELOPMENT tooling).

AREPO never trades. Everything here is a paper calculation on public data.

Fill accounting (one public fill, as served by the Data API with ``takerOnly=true``: the row is the
taker's side; the maker is the other side of the same fill)
--------------------------------------------------------------------------------------------------
* ``d0`` = +1 when the taker ends long outcome 0 (BUY outcome 0, or SELL outcome 1), else -1.
* ``p0`` = the fill price in outcome-0 terms (``p`` for outcome 0, ``1 - p`` for outcome 1).
* ``y0`` = 1 if outcome 0 won, 0 if it lost (50/50 and unresolved markets are excluded upstream).
* taker gross P&L per share = ``d0 * (y0 - p0)``; maker gross P&L per share = ``-d0 * (y0 - p0)``.
  Pre-fee the two are an exact zero-sum identity per fill. The informative quantities are therefore the
  maker's gross edge per contract (= minus the taker's), per-dollar returns (whose denominators differ:
  each side pays the price of the token it bought), and what fees, rebates and rewards add on each side.
* maker cost per share = price of the token the maker bought: ``p0`` if the maker is long outcome 0,
  else ``1 - p0``. Taker cost is the complement price.
* taker fee per share = ``rate * p * (1 - p)`` (symmetric in ``p0``); maker rebate per share =
  ``rebate_share * fee`` (the optimistic pro-rata assumption of ECON part B; the docs allocate the
  per-market pool pro rata to fee-equivalent, so a single maker's share is at most this).

Liquidity-reward score (docs.polymarket.com/market-makers/liquidity-rewards, fetched 2026-10-19)
--------------------------------------------------------------------------------------------------
``S(v, s) = ((v - s) / v)^2`` per share for an order ``s`` from the (size-adjusted) mid within max
spread ``v``; ``Q_one`` = bid-side score on m plus ask-side score on the complement, ``Q_two`` the
reverse; for mid in [0.10, 0.90] ``Q_min = max(min(Q1, Q2), max(Q1, Q2) / c)`` with ``c = 3``; outside
that range ``Q_min = min(Q1, Q2)``. A maker's daily share is its summed per-minute normalised ``Q_min``
over 1,440 samples. With a stationary book the share is ``Q_ours / (Q_ours + sum_i Q_min_i)``.
The competitor sum is not observable from public summary depth, so it is BOUNDED here (see
``competitor_qmin_bounds``) and every reward figure is reported as a [low, high] interval.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field

import numpy as np

VERSION = "maker-rewards-dev-v1"

# ---------------------------------------------------------------------------------------------
# Fee facts (docs.polymarket.com/trading/fees, fetched 2026-10-19) and rollout dates
# (PRIOR_ART_2026-10-19.md section 2.6: crypto 15-min 2026-01-05, sports 02-18, all crypto 03-06,
# most categories 03-30). The historical per-market schedule is NOT in the history frames, so fee
# and rebate figures are a SECONDARY, docs-based reconstruction; the primary statistic is pre-fee.
# ---------------------------------------------------------------------------------------------
DOCS_RATE = {"crypto": 0.07, "sports": 0.05, "economics": 0.05, "culture": 0.05, "weather": 0.05,
             "other": 0.05, "finance": 0.04, "politics": 0.04, "mentions": 0.04, "tech": 0.04,
             "geopolitics": 0.0}
REBATE_SHARE = {"crypto": 0.20, "sports": 0.15, "finance": 0.25, "politics": 0.25, "economics": 0.25,
                "culture": 0.25, "weather": 0.25, "other": 0.25, "mentions": 0.25, "tech": 0.25,
                "geopolitics": 0.0}
FEE_FROM_UTC = {"crypto": 1772755200,   # 2026-03-06T00:00Z (all crypto; 15-min from 01-05 not separable)
                "sports": 1771372800,   # 2026-02-18T00:00Z
                "default": 1774828800}  # 2026-03-30T00:00Z
REWARD_C = 3.0
TWO_SIDED_ONLY_OUTSIDE = (0.10, 0.90)

CLASSES = ("sports", "crypto_short", "crypto_other", "negrisk_multi", "politics_binary", "single_binary")
HORIZON_BANDS = ((0.0, 86400.0, "h<1d"), (86400.0, 7 * 86400.0, "h1-7d"),
                 (7 * 86400.0, 30 * 86400.0, "h7-30d"), (30 * 86400.0, math.inf, "h>30d"))
PRICE_BANDS = ((0.0, 0.10, "p<0.10"), (0.10, 0.30, "p0.10-0.30"), (0.30, 0.50, "p0.30-0.50"),
               (0.50, 0.70, "p0.50-0.70"), (0.70, 0.90, "p0.70-0.90"), (0.90, 1.0001, "p>=0.90"))
CRYPTO_SHORT_LIFETIME_S = 25 * 3600.0


def fee_key(fee_category: str | None) -> str:
    """Normalise a frame ``fee_category`` (e.g. ``other:zero_fees``) to a docs table key."""
    c = str(fee_category or "unknown").strip().lower()
    if c.startswith("other:zero"):
        return "geopolitics"  # fee-free, no rebate
    return c.split(":", 1)[0]


def docs_fee_rate(fee_category: str | None, ts: float) -> float:
    """Docs taker rate in force at ``ts`` (0 before the category's rollout or for unknown categories)."""
    k = fee_key(fee_category)
    if k not in DOCS_RATE:
        return 0.0
    start = FEE_FROM_UTC.get(k, FEE_FROM_UTC["default"])
    return DOCS_RATE[k] if ts >= start else 0.0


def parse_resolution(outcome_prices: str | None) -> float | None:
    """1.0 if outcome 0 won, 0.0 if outcome 1 won, None otherwise (50/50, unresolved, malformed)."""
    try:
        v = json.loads(outcome_prices) if isinstance(outcome_prices, str) else outcome_prices
        a, b = float(v[0]), float(v[1])
    except (TypeError, ValueError, IndexError, json.JSONDecodeError):
        return None
    if a >= 0.99 and b <= 0.01:
        return 1.0
    if b >= 0.99 and a <= 0.01:
        return 0.0
    return None


def market_class(fee_category: str | None, neg_risk: int | bool, start_epoch: float, end_epoch: float) -> str:
    """Primary class, first match wins: sports (flagged separately), crypto_short (lifetime <= 25 h: the
    up/down proxy usable on frames without text), crypto_other, negrisk_multi (neg-risk member of a
    multi-outcome event), politics_binary, single_binary (every other standalone binary)."""
    k = fee_key(fee_category)
    if k == "sports":
        return "sports"
    if k == "crypto":
        life = end_epoch - start_epoch
        return "crypto_short" if (math.isfinite(life) and 0 < life <= CRYPTO_SHORT_LIFETIME_S) else "crypto_other"
    if bool(int(neg_risk or 0)):
        return "negrisk_multi"
    if k == "politics":
        return "politics_binary"
    return "single_binary"


def band(x: float, bands) -> str:
    for lo, hi, name in bands:
        if lo <= x < hi:
            return name
    return "na"


def fill_arrays(side: np.ndarray, outcome_index: np.ndarray, price: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """``(d0, p0)`` for taker rows (see the module docstring)."""
    buy = np.where(side == "BUY", 1, -1)
    d0 = np.where(outcome_index == 0, buy, -buy)
    p0 = np.where(outcome_index == 0, price, 1.0 - price)
    return d0.astype(float), p0.astype(float)


def per_fill(side, outcome_index, price, size, ts, y0: float, fee_category: str | None) -> dict[str, np.ndarray]:
    """Per-share quantities for one market's taker rows (arrays)."""
    side = np.asarray(side).astype(str)
    oi = np.asarray(outcome_index).astype(int)
    p = np.asarray(price, dtype=float)
    q = np.asarray(size, dtype=float)
    t = np.asarray(ts, dtype=float)
    d0, p0 = fill_arrays(side, oi, p)
    maker_pnl = -d0 * (y0 - p0)
    maker_long0 = -d0 > 0
    maker_cost = np.where(maker_long0, p0, 1.0 - p0)
    taker_cost = 1.0 - maker_cost
    rate = np.array([docs_fee_rate(fee_category, x) for x in t]) if len(t) else np.zeros(0)
    fee = rate * p0 * (1.0 - p0)
    rebate = REBATE_SHARE.get(fee_key(fee_category), 0.0) * fee
    return {"maker_pnl": maker_pnl, "maker_cost": maker_cost, "taker_cost": taker_cost, "fee": fee,
            "rebate": rebate, "size": q, "ts": t, "p0": p0}


# ---------------------------------------------------------------------------------------------
# Aggregation: sums per (unit, class, horizon band, maker price band); cells marginalise later.
# ---------------------------------------------------------------------------------------------
SUM_FIELDS = ("n", "shares", "pnl", "mcost", "tcost", "fee", "rebate", "pnl_fill")


@dataclass
class Accumulator:
    sums: dict = field(default_factory=lambda: defaultdict(lambda: np.zeros(len(SUM_FIELDS))))
    counts: dict = field(default_factory=lambda: defaultdict(int))

    def add_market(self, unit: str, mclass: str, close_epoch: float, f: dict[str, np.ndarray]) -> None:
        if not len(f["size"]):
            return
        hz = close_epoch - f["ts"]
        hb = np.array([band(x, HORIZON_BANDS) for x in hz])
        pb = np.array([band(x, PRICE_BANDS) for x in f["maker_cost"]])
        for h in np.unique(hb):
            for pbn in np.unique(pb):
                m = (hb == h) & (pb == pbn)
                if not m.any():
                    continue
                s = f["size"][m]
                self.sums[(unit, mclass, h, pbn)] += np.array([
                    m.sum(), s.sum(), (f["maker_pnl"][m] * s).sum(), (f["maker_cost"][m] * s).sum(),
                    (f["taker_cost"][m] * s).sum(), (f["fee"][m] * s).sum(), (f["rebate"][m] * s).sum(),
                    f["maker_pnl"][m].sum()])

    def unit_table(self, classes: Iterable[str] | None = None, horizons: Iterable[str] | None = None,
                   pbands: Iterable[str] | None = None) -> tuple[list[str], np.ndarray]:
        """Per-unit summed fields for the selected cell (None = all)."""
        cs, hs, ps = (set(x) if x is not None else None for x in (classes, horizons, pbands))
        agg: dict[str, np.ndarray] = defaultdict(lambda: np.zeros(len(SUM_FIELDS)))
        for (u, c, h, p), v in self.sums.items():
            if (cs is None or c in cs) and (hs is None or h in hs) and (ps is None or p in ps):
                agg[u] += v
        units = sorted(agg)
        return units, (np.vstack([agg[u] for u in units]) if units else np.zeros((0, len(SUM_FIELDS))))


def _boot_idx(n: int, n_boot: int, seed: int) -> np.ndarray:
    return np.random.default_rng(seed).integers(0, n, size=(n_boot, n))


def summarise(table: np.ndarray, n_boot: int = 2000, seed: int = 20261020, min_units: int = 30) -> dict:
    """Cell statistics in CENTS per share (returns in %), with percentile CIs from a bootstrap over units
    (one unit per event: the event is the resampling cluster).

    PRIMARY (``*_pooled``): pooled ratio sum(pnl * size) / sum(size) over all fills of the cell. With a
    calibrated (martingale) price every fill has zero expected P&L whatever the predictable rule that picks
    it, so this ratio is consistent for zero under the null.
    SECONDARY: ``*_pooled_fill`` weights every fill equally (robust to a few giant prints).
    REFERENCE ONLY, BIASED: ``*_unit_mean`` (equal weight per event of the event's own ratio). Normalising by
    the event's total fill volume uses the future path, and simulation of a calibrated market shows biases
    of about +1c (class cells) to +/-5.5c (maker price-band cells); never read it as an effect."""
    n = int(table.shape[0])
    out: dict = {"units": n, "fills": int(table[:, 0].sum()) if n else 0,
                 "shares": float(table[:, 1].sum()) if n else 0.0}
    if n < min_units:
        out["status"] = f"not estimated (< {min_units} units)"
        return out
    cnt, sh, pnl, mc, tc, fee, reb, pf = (table[:, i] for i in range(8))
    idx = _boot_idx(n, n_boot, seed)

    def stat(fn) -> tuple[float, list[float]]:
        b = np.array([fn(i) for i in idx])
        return float(fn(slice(None))), [float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))]

    out["status"] = "estimated"
    for name, fn in (
        ("maker_gross_c_pooled", lambda i: 100.0 * pnl[i].sum() / sh[i].sum()),
        ("maker_gross_c_pooled_fill", lambda i: 100.0 * pf[i].sum() / cnt[i].sum()),
        ("maker_net_c_pooled", lambda i: 100.0 * (pnl[i].sum() + reb[i].sum()) / sh[i].sum()),
        ("taker_net_c_pooled", lambda i: 100.0 * (-pnl[i].sum() - fee[i].sum()) / sh[i].sum()),
        ("maker_return_pct_pooled", lambda i: 100.0 * pnl[i].sum() / mc[i].sum()),
        ("taker_return_pct_pooled", lambda i: 100.0 * (-pnl[i].sum() - fee[i].sum()) / tc[i].sum()),
    ):
        out[name], out[name + "_ci"] = stat(fn)
    out["fee_c_pooled"] = float(100.0 * fee.sum() / sh.sum())
    out["rebate_c_pooled"] = float(100.0 * reb.sum() / sh.sum())
    unit_pc = 100.0 * pnl / sh
    out["maker_gross_c_unit_mean_BIASED_reference"] = float(unit_pc.mean())
    out["unit_ratio_sd_c"] = float(unit_pc.std(ddof=1))
    # top-5 events' share of the cell's shares (concentration of the pooled estimate)
    out["top5_unit_share_of_shares"] = float(np.sort(sh)[-5:].sum() / sh.sum())
    out["maker_gross_c_pooled_drop_top5"] = float(100.0 * (pnl.sum() - pnl[np.argsort(sh)[-5:]].sum())
                                                  / (sh.sum() - np.sort(sh)[-5:].sum())) if n > 5 else math.nan
    return out


# ---------------------------------------------------------------------------------------------
# Liquidity rewards
# ---------------------------------------------------------------------------------------------

def reward_score(v: float, s: float, b: float = 1.0) -> float:
    """Per-share score ``((v - s)/v)^2 * b`` for ``0 <= s < v`` (prices in the same unit), else 0."""
    if not (v > 0) or s < 0 or s >= v:
        return 0.0
    return ((v - s) / v) ** 2 * b


def q_min(q_one: float, q_two: float, mid: float, c: float = REWARD_C) -> float:
    lo, hi = TWO_SIDED_ONLY_OUTSIDE
    if lo <= mid <= hi:
        return max(min(q_one, q_two), max(q_one, q_two) / c)
    return min(q_one, q_two)


def parse_daily_rate(clob_rewards: str | None, day: str | None = None) -> float:
    """Sum of ``rewardsDailyRate`` over the Gamma ``clobRewards`` allocations active on ``day``
    (YYYY-MM-DD; None = all). Empty / malformed = 0.0 (no native programme seen)."""
    try:
        arr = json.loads(clob_rewards) if isinstance(clob_rewards, str) and clob_rewards else []
    except json.JSONDecodeError:
        return 0.0
    tot = 0.0
    for a in arr if isinstance(arr, list) else []:
        if not isinstance(a, dict):
            continue
        if day is not None:
            sd, ed = str(a.get("startDate") or "")[:10], str(a.get("endDate") or "")[:10]
            if (sd and day < sd) or (ed and day > ed):
                continue
        try:
            tot += float(a.get("rewardsDailyRate") or 0.0)
        except (TypeError, ValueError):
            continue
    return tot


def _side_buckets(best: float, size1: float, d1c: float, d5c: float, sign: int, mid: float) -> list[tuple[float, float, float]]:
    """Depth buckets ``(size, near_distance, far_distance)`` from the mid, from book-sweep summary depth:
    the touch, (0, 1c] behind the touch, (1c, 5c] behind it. ``sign`` +1 for asks, -1 for bids."""
    h = abs(best - mid)
    size1 = max(size1, 0.0)
    b1 = max((d1c if math.isfinite(d1c) else size1) - size1, 0.0)
    b5 = max((d5c if math.isfinite(d5c) else 0.0) - (d1c if math.isfinite(d1c) else size1), 0.0)
    return [(size1, h, h), (b1, h + 1e-9, h + 0.01), (b5, h + 0.01, h + 0.05)]


def _bucket_score(buckets, v: float, near: bool) -> float:
    return sum(sz * reward_score(v, (lo if near else hi)) for sz, lo, hi in buckets)


def competitor_qmin_bounds(tok0: dict, tok1: dict | None, v: float) -> tuple[float, float, float]:
    """``(mid, low, high)`` bounds on the competitors' summed ``Q_min``.

    ``tok0``/``tok1``: book-sweep rows (``best_bid, best_ask, bid_size_1, ask_size_1, depth_bid_1c,
    depth_ask_1c, depth_bid_5c, depth_ask_5c``). Distances: the near edge of each bucket gives the
    high score, the far edge the low score. Aggregation over unknown makers: in [0.10, 0.90]
    ``sum Q_min_i`` lies in ``[(Q1 + Q2) / (2c), Q1 + Q2]``; outside it in ``[0, (Q1 + Q2) / 2]``
    (two-sided only). ``v`` in price units (cents / 100)."""
    bb, ba = float(tok0["best_bid"]), float(tok0["best_ask"])
    mid = 0.5 * (bb + ba)

    def side(t: dict, which: str, m: float) -> list:
        best = float(t[f"best_{which}"])
        return _side_buckets(best, float(t[f"{which}_size_1"] or 0.0), float(t.get(f"depth_{which}_1c") or math.nan),
                             float(t.get(f"depth_{which}_5c") or math.nan), +1 if which == "ask" else -1, m)

    b0, a0 = side(tok0, "bid", mid), side(tok0, "ask", mid)
    if tok1 is not None and all(tok1.get(k) not in (None, "") for k in ("best_bid", "best_ask")):
        m1 = 1.0 - mid
        b1, a1 = side(tok1, "bid", m1), side(tok1, "ask", m1)
    else:
        b1, a1 = [], []
    out = []
    for near in (False, True):
        q1 = _bucket_score(b0, v, near) + _bucket_score(a1, v, near)
        q2 = _bucket_score(a0, v, near) + _bucket_score(b1, v, near)
        out.append((q1, q2))
    lo_mid, hi_mid = TWO_SIDED_ONLY_OUTSIDE
    (q1l, q2l), (q1h, q2h) = out
    if lo_mid <= mid <= hi_mid:
        low, high = (q1l + q2l) / (2 * REWARD_C), q1h + q2h
    else:
        low, high = 0.0, (q1h + q2h) / 2.0
    return mid, low, high


def paper_quote_reward(rate_per_day: float, v_cents: float, min_size: float, tok0: dict, tok1: dict | None) -> dict | None:
    """Expected daily reward of ONE paper two-sided quote of ``min_size`` shares per side on outcome 0, posted
    at ``s = max(v/2, half-spread)`` from the mid (never inside the touch), under a stationary book.
    Returns low/high reward bounds, the capital locked and the implied daily yield; None if not scorable."""
    try:
        v = float(v_cents) / 100.0
        bb, ba = float(tok0["best_bid"]), float(tok0["best_ask"])
    except (TypeError, ValueError, KeyError):
        return None
    if not (rate_per_day > 0 and v > 0 and min_size > 0 and 0 < bb < ba < 1):
        return None
    mid, comp_low, comp_high = competitor_qmin_bounds(tok0, tok1, v)
    s = max(v / 2.0, (ba - bb) / 2.0)
    sc = reward_score(v, s)
    ours = q_min(sc * min_size, sc * min_size, mid)
    if ours <= 0:
        return {"mid": mid, "s": s, "ours_q": 0.0, "reward_low": 0.0, "reward_high": 0.0,
                "capital": math.nan, "yield_low": 0.0, "yield_high": 0.0, "scorable": False}
    capital = min_size * max(mid - s, 0.0) + min_size * max(1.0 - (mid + s), 0.0)
    r_low, r_high = rate_per_day * ours / (ours + comp_high), rate_per_day * ours / (ours + comp_low)
    return {"mid": mid, "s": s, "ours_q": ours, "comp_low": comp_low, "comp_high": comp_high,
            "reward_low": r_low, "reward_high": r_high, "capital": capital,
            "yield_low": r_low / capital if capital > 0 else math.nan,
            "yield_high": r_high / capital if capital > 0 else math.nan, "scorable": True}
