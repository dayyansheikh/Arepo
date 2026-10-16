# ruff: noqa: E501
"""CB3 family B and the shared paper maker (docs/research_lab/CREATIVE_BATCH_3.md §2.1, §2.6, §3 CB3-B, §4.1).

Selective maker (CH39 post-print retreat, CH40 late-life schedule, CH41-narrow round-trip share) against the unfiltered
maker U. Prices and mark-outs are in price units (1c = 0.01). Paper rules only; no trading, no rewards in any primary.

Pure functions over arrays/DataFrames; the history loader reads the pmxt book table and h2 trades through the CB1 history
helpers (imported, not copied), the prospective loader reads ``quote_state/`` and ``cb3_followup/`` through
:class:`FollowupReader`. Family A re-uses the maker (fills, rebate, marks) from here for A3.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from . import bounce_decomp as bd
from . import cb1_history as c1
from . import cb3_common as C
from . import cb3_declaration as D
from . import economics

OWN = D.MAKER["order_shares"]
LIFE = float(D.MAKER["life_s"])
MARK_S = float(D.MAKER["mark_s"])
MARK2_S = float(D.MAKER["mark_secondary_s"])
VISIBLE = int(D.MAKER["visible_prints"])
HOUR = 3600.0
DAY = 86400.0
RULES = ("queue", "touch")
SIDES = ("bid", "ask")


# =============================================================================================
# 1. Rebate and fees (maker fee 0; rebate pro rata; unknown category -> 0)
# =============================================================================================


def category_key(cat) -> str:
    if cat is None or (isinstance(cat, float) and math.isnan(cat)):
        return ""
    return str(cat).split(":")[0].strip().lower()


def rebate_share(cat) -> float:
    return float(economics.REBATE_SHARE.get(category_key(cat), D.MAKER["rebate_unknown_category"]))


def _fees_flag(v) -> bool | None:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    t = str(v).strip().lower()
    if t in ("1", "1.0", "true"):
        return True
    if t in ("0", "0.0", "false"):
        return False
    return None


def fee_rate(cat, fee_schedule=None, *, fees_enabled=None, prospective: bool = False) -> float:
    """Rate used for INCOME (the rebate): the docs table by category in history (unknown category -> 0); prospectively the minimum of
    the as-of ``fee_schedule`` rate and the docs rate, 0 when the schedule is unknown or fees are disabled (freeze-check fix 6)."""
    key = category_key(cat)
    docs = economics.DOCS_CATEGORY_RATE.get(key)
    if not prospective:
        return float(docs) if docs is not None else 0.0
    spec = economics.fee_spec(fee_schedule if fee_schedule not in ("", None) else None, _fees_flag(fees_enabled), key or None)
    if not spec.known:
        return 0.0
    return float(min(spec.rate, docs)) if docs is not None else float(spec.rate)


def rebate_per_share(price: float, cat, *, fee_schedule=None, fees_enabled=None, prospective: bool = False, halved: bool = False) -> float:
    """``rho_cat * r_cat * P (1 - P)`` per filled share (maker fee 0). Unknown/null category: rho = 0; unknown fee schedule: 0."""
    rho = rebate_share(cat)
    if rho == 0.0:
        return 0.0
    out = rho * fee_rate(cat, fee_schedule, fees_enabled=fees_enabled, prospective=prospective) * float(price) * (1.0 - float(price))
    return out * (0.5 if halved else 1.0)


# =============================================================================================
# 2. Prints: outcome-0 arrays, visibility, union, taker orders
# =============================================================================================


def prints_arrays(df: pd.DataFrame | None) -> dict[str, np.ndarray]:
    """Prints of one market in outcome-0 terms, sorted by ts (stable): ``ts``, ``p0``, ``buy`` (taker buys outcome 0:
    BUY of 0 or SELL of 1, the ``cb1_history.buys_longshot`` convention), ``size``, ``wallet``, ``notional`` (own-token
    size x price), ``side_raw``, ``outcome``, ``key``. Rows with bad side/outcome are dropped."""
    empty = {k: np.empty(0) for k in ("ts", "p0", "size", "notional", "outcome")}
    empty.update(buy=np.empty(0, bool), wallet=np.empty(0, object), side_raw=np.empty(0, object), key=np.empty(0, object))
    if df is None or len(df) == 0:
        return empty
    t = df[df["outcome_index"].isin([0, 1]) & df["side"].isin(["BUY", "SELL"])].copy()
    t = t.sort_values("ts", kind="stable")
    oi = t["outcome_index"].to_numpy()
    o1 = oi == 1
    price = t["price"].to_numpy(float)
    side = t["side"].to_numpy()
    n = len(t)
    wallet = t["wallet_hash"].fillna("").astype(str).to_numpy() if "wallet_hash" in t else np.full(n, "", object)
    if "tx_hash" in t:
        key = t["tx_hash"].fillna("").astype(str).to_numpy()
    elif "trade_key" in t:
        key = t["trade_key"].fillna("").astype(str).to_numpy()
    else:
        key = np.array([f"{a}|{b}|{c}|{d}|{e}" for a, b, c, d, e in zip(t["ts"], side, oi, price, t["size"], strict=True)], object)
    return {"ts": t["ts"].to_numpy(float), "p0": np.where(o1, 1.0 - price, price), "buy": (side == "BUY") != o1,
            "size": t["size"].to_numpy(float), "wallet": wallet, "notional": t["size"].to_numpy(float) * price,
            "side_raw": side.astype(object), "outcome": oi.astype(float), "key": key}


def _take(pr: dict[str, np.ndarray], mask: np.ndarray) -> dict[str, np.ndarray]:
    return {k: v[mask] for k, v in pr.items()}


def visible_prints(pr: dict[str, np.ndarray], t: float, n: int = VISIBLE) -> dict[str, np.ndarray]:
    """The newest ``n`` prints strictly before ``t`` (ruling 1: the prospective 500-print page, mimicked in history)."""
    hi = np.searchsorted(pr["ts"], t, side="left")
    lo = max(0, hi - n)
    sel = np.zeros(len(pr["ts"]), bool)
    sel[lo:hi] = True
    return _take(pr, sel)


def _dedupe_keys(pr: dict[str, np.ndarray]) -> list[tuple]:
    return [(str(sd), float(o), round(float(p), 8), round(float(z), 8), float(ts), str(w)) for sd, o, p, z, ts, w in
            zip(pr["side_raw"], pr["outcome"], pr["p0"], pr["size"], pr["ts"], pr["wallet"], strict=True)]


def prints_union(pre: dict[str, np.ndarray], post: dict[str, np.ndarray], t: float) -> dict[str, np.ndarray]:
    """pre/ filtered to ``ts < t``, post/ to ``ts > t``, then de-duplicated ACROSS the two sources (a print present in both
    counts once; identical prints inside one source are kept, they can be genuine split fills), time-sorted (item 5).
    The key is (side, outcome, price, size, ts, wallet hash): the stored sources do not share a transaction id."""
    a = _take(pre, pre["ts"] < t) if len(pre["ts"]) else pre
    b = _take(post, post["ts"] > t) if len(post["ts"]) else post
    if len(b["ts"]) and len(a["ts"]):
        seen = set(_dedupe_keys(a))
        keep = np.array([k not in seen for k in _dedupe_keys(b)], bool)
        b = _take(b, keep)
    cat = {k: np.concatenate([a[k], b[k]]) for k in a}
    if not len(cat["ts"]):
        return cat
    o = np.argsort(cat["ts"], kind="stable")
    return {k: v[o] for k, v in cat.items()}


def taker_orders(pr: dict[str, np.ndarray]) -> pd.DataFrame:
    """Taker orders: prints with the same (tx/trade group where known) else (ts, wallet, side, outcome) aggregated.
    History has no transaction id, so the group is (ts, wallet_hash, side, outcome_index). Notional = sum size x price."""
    if not len(pr["ts"]):
        return pd.DataFrame({"ts": [], "notional": [], "wallet": [], "buy": [], "n_prints": []})
    df = pd.DataFrame({"ts": pr["ts"], "wallet": pr["wallet"], "side": pr["side_raw"], "outcome": pr["outcome"], "notional": pr["notional"]})
    g = df.groupby(["ts", "wallet", "side", "outcome"], sort=True).agg(notional=("notional", "sum"), n_prints=("notional", "size")).reset_index()
    g["buy"] = (g["side"] == "BUY") != (g["outcome"] == 1)
    return g[["ts", "notional", "wallet", "buy", "n_prints"]].sort_values("ts", kind="stable").reset_index(drop=True)


def large_order_flags(ts: np.ndarray, notional: np.ndarray, *, window: int = D.B["large_order_window_orders"],
                      min_prior: int = D.B["large_order_min_prior"], pct: float = D.B["large_order_pct"]) -> np.ndarray:
    """1.0 if the order's notional >= the ``pct`` percentile of the market's previous ``window`` taker orders (strictly
    earlier timestamps; same-ts orders never count as prior), 0.0 if not, NaN (unclassified) with fewer than ``min_prior``
    prior orders. The order itself is never part of its own reference."""
    n = len(ts)
    out = np.full(n, np.nan)
    if n == 0:
        return out
    lo = np.searchsorted(ts, ts, side="left")
    for k in range(n):
        j = int(lo[k])
        if j < min_prior:
            continue
        prior = notional[max(0, j - window):j]
        out[k] = 1.0 if notional[k] >= np.percentile(prior, pct) else 0.0
    return out


def life_fraction(t: float, created: float, end: float) -> float:
    """``(t - created_at) / (end_at - created_at)`` clipped to [0, 1], from the SCHEDULED ``end_at`` only (``closed_time``
    is never an anchor). NaN when either anchor is missing or the schedule is degenerate."""
    if not (math.isfinite(created) and math.isfinite(end)) or end <= created:
        return math.nan
    return float(min(1.0, max(0.0, (t - created) / (end - created))))


def round_trip_share(vis: dict[str, np.ndarray], t: float, *, truncated: bool = False, oldest_ts: float | None = None) -> float:
    """Within-market round-trip share (CH41-narrow). A wallet is a round-tripper at t if, over its prints in
    [t-24h, t): >= 4 trades, both signs on outcome 0, |sum signed shares| <= 0.10 sum |shares|. RT = notional share of the
    prints in [t-6h, t) from round-trippers. Undefined (NaN) when < 20 prints in [t-6h, t) or when the visible newest
    500 prints do not reach back to t-24h."""
    ts = vis["ts"]
    w24, w6 = t - D.B["rt_wallet_window_s"], t - D.B["rt_share_window_s"]
    n = len(ts)
    if n >= VISIBLE:
        if ts[0] > w24:
            return math.nan
    elif truncated and (oldest_ts is None or not math.isfinite(float(oldest_ts)) or float(oldest_ts) > w24):
        return math.nan
    in24 = ts >= w24
    in6 = ts >= w6
    if int(in6.sum()) < D.B["rt_min_prints"]:
        return math.nan
    df = pd.DataFrame({"w": vis["wallet"][in24], "sg": np.where(vis["buy"][in24], 1.0, -1.0), "sz": vis["size"][in24]})
    df["ss"] = df["sg"] * df["sz"]
    g = df.groupby("w").agg(n=("sz", "size"), pos=("sg", lambda s: (s > 0).any()), neg=("sg", lambda s: (s < 0).any()),
                            net=("ss", "sum"), gross=("sz", "sum"))
    rt = g[(g["n"] >= D.B["rt_min_trades"]) & g["pos"] & g["neg"] & (g["net"].abs() <= D.B["rt_net_frac"] * g["gross"]) & (g.index != "")].index
    tot = float(vis["notional"][in6].sum())
    if not tot > 0:
        return math.nan
    return float(vis["notional"][in6 & np.isin(vis["wallet"], list(rt))].sum() / tot)


# =============================================================================================
# 3. Fills: queue rule (primary, cb1_history.queue_fill) and touch rule; unavailable statuses
# =============================================================================================


def _side_tuple(pr: dict[str, np.ndarray], c: int):
    if c == 0:
        return pr["ts"], pr["p0"], pr["buy"], pr["size"]
    return pr["ts"], 1.0 - pr["p0"], ~pr["buy"], pr["size"]


def quote_fills(pr: dict[str, np.ndarray], t: float, side: str, price: float, depth: float, *, life: float = LIFE,
                own: float = OWN, truncated: bool = False, oldest_ts: float | None = None) -> dict:
    """Fill status of one resting quote over (t, t + life) for BOTH rules.

    side 'bid': filled by taker sells of outcome 0 at <= price (= taker buys of outcome 1 at >= 1 - price; the
    ``buys_longshot`` conversion); side 'ask': by taker buys of outcome 0 at >= price. Queue rule = ``cb1_history.queue_fill``
    (cumulative opposite-aggressor volume at or through the price reaches ``depth`` + ``own``; a print exactly at t is not in
    the window). Touch rule = any such print. Status 1 filled, 0 not, -1 unavailable: the window begins before a truncated
    market's oldest stored print (CB1 section 2.2), never 0."""
    if side not in SIDES:
        raise ValueError(side)
    tup = _side_tuple(pr, 0 if side == "ask" else 1)
    a_c = float(price) if side == "ask" else 1.0 - float(price)
    q = c1.queue_fill(tup, t, a_c, depth, own=own, life=life)
    ts, cp, buy, _sz = tup
    lo, hi = np.searchsorted(ts, t, side="right"), np.searchsorted(ts, t + life, side="left")
    ok = buy[lo:hi] & (cp[lo:hi] >= a_c - 1e-9)
    t_touch = float(ts[lo:hi][ok][0]) if ok.any() else math.nan
    unavailable = bool(truncated and (oldest_ts is None or not math.isfinite(float(oldest_ts)) or t < float(oldest_ts)))
    out = {}
    for rule, filled, tf in (("queue", q["filled"], q["t_fill"]), ("touch", bool(ok.any()), t_touch)):
        out[rule] = (-1, math.nan) if unavailable else ((1, float(tf)) if filled else (0, math.nan))
    return out


# =============================================================================================
# 4. Marks: history (price series) and prospective (tight first sweeps), far-touch worst case
# =============================================================================================


class HistoryMarks:
    """Marks from a market's price series (``cb1_history.asof_quote``: stamp + 600 s, at most 2h old)."""

    def __init__(self, ts: np.ndarray, vals: np.ndarray) -> None:
        self.ts, self.vals = np.asarray(ts, float), np.asarray(vals, float)

    def mark(self, t_fill: float, h: float, hs: float) -> tuple[float, float, float]:
        m = float(c1.asof_quote(self.ts, self.vals, np.array([t_fill + h]))[0]) if len(self.ts) else math.nan
        return m, m - hs, m + hs

    def last_before(self, t_limit: float, hs: float, after: float) -> tuple[float, float]:
        """(bid, ask) of the last price point at or before ``t_limit`` and after the fill (history: mid -/+ entry half-spread)."""
        if not len(self.ts):
            return math.nan, math.nan
        i = int(np.searchsorted(self.ts, t_limit, side="right")) - 1
        if i < 0 or self.ts[i] <= after:  # only points stamped after the fill count
            return math.nan, math.nan
        return float(self.vals[i]) - hs, float(self.vals[i]) + hs


class SweepMarks:
    """Prospective marks: the first-sweep books of one market over passes (``recv`` receipt epoch, bid, ask).

    ``mark``: the first pass with receipt >= t_fill + h whose book is E001-tight (two-sided, spread <= 0.10); if that pass is
    not tight, the next pass within 4h of t_fill + h; else unavailable. The worst case for an unavailable mark is the far
    touch of the last available sweep in (t_fill, t_fill + h + 4h]."""

    def __init__(self, recv: np.ndarray, bid: np.ndarray, ask: np.ndarray) -> None:
        o = np.argsort(np.asarray(recv, float), kind="stable")
        self.recv, self.bid, self.ask = np.asarray(recv, float)[o], np.asarray(bid, float)[o], np.asarray(ask, float)[o]

    def _tight(self) -> np.ndarray:
        mid = (self.bid + self.ask) / 2.0
        return (np.isfinite(self.bid) & np.isfinite(self.ask) & (self.bid < self.ask) & (self.ask < 1) & ((self.ask - self.bid) <= D.MAKER["spread_max"] + 1e-12)
                & (mid >= D.A["tight_mid_band"][0]) & (mid <= D.A["tight_mid_band"][1]))

    def mark(self, t_fill: float, h: float, hs: float = 0.0) -> tuple[float, float, float]:
        t0 = t_fill + h
        lim = t0 + float(D.MAKER["prospective_mark_next_pass_within_s"])
        tight = self._tight()
        idx = np.flatnonzero((self.recv >= t0) & (self.recv <= lim) & tight)
        if not len(idx):
            return math.nan, math.nan, math.nan
        i = int(idx[0])
        return (self.bid[i] + self.ask[i]) / 2.0, float(self.bid[i]), float(self.ask[i])

    def last_before(self, t_limit: float, hs: float, after: float) -> tuple[float, float]:
        ok = np.flatnonzero((self.recv > after) & (self.recv <= t_limit + float(D.MAKER["prospective_mark_next_pass_within_s"])) & np.isfinite(self.bid) & np.isfinite(self.ask))
        if not len(ok):
            return math.nan, math.nan
        return float(self.bid[ok[-1]]), float(self.ask[ok[-1]])


def mark_out(side: str, price: float, mark: float) -> float:
    """Buy fill at P (our bid): M - P. Sell fill at P (our ask): P - M."""
    return float(mark - price) if side == "bid" else float(price - mark)


def worst_case_mo(side: str, price: float, far_bid: float, far_ask: float) -> float:
    """Taker exit at the far touch (bid for a bought position, ask for a sold one); no mark at all -> total loss
    (buy value 0, sell value 1)."""
    if side == "bid":
        return float(far_bid - price) if math.isfinite(far_bid) else float(-price)
    return float(price - far_ask) if math.isfinite(far_ask) else float(-(1.0 - price))


# =============================================================================================
# 5. Per-opportunity evaluation
# =============================================================================================


@dataclass
class Opp:
    """One quote opportunity (inputs); ``pre``/``post`` are print dicts from :func:`prints_arrays`."""

    opp_id: str
    market_id: str
    event: str
    dep: str
    cat: str
    t: float
    bid: float
    ask: float
    bid_size: float
    ask_size: float
    created: float = math.nan
    end: float = math.nan
    abs_chg_24h: float = math.nan
    depth_1c_own: float = math.nan  # bid-side 1c depth
    depth_1c_ask: float = math.nan
    depth_1c_both: float = math.nan
    fee_schedule: object = None
    fees_enabled: object = None
    pre_truncated: bool | None = None  # the pre-origin page (trade sample, 500-print cap) reached its cap / failed; None = same as ``truncated``
    pre_oldest: float | None = None
    truncated: bool = False
    oldest_ts: float | None = None
    life: float = LIFE
    life_truncated: bool = False


def _grid_band(x: float, edges) -> int:
    return int(np.searchsorted(np.asarray(edges, float), x, side="right"))


def eligible_quote(bid: float, ask: float) -> bool:
    """Two-sided, non-crossed book, spread <= 0.10, mid in [0.10, 0.90]."""
    if not (math.isfinite(bid) and math.isfinite(ask)) or not bid < ask:
        return False
    mid = (bid + ask) / 2.0
    return (ask - bid) <= D.MAKER["spread_max"] + 1e-12 and D.MAKER["mid_band"][0] <= mid <= D.MAKER["mid_band"][1]


def evaluate_opportunity(o: Opp, pre: dict[str, np.ndarray], post: dict[str, np.ndarray], marks, *, prospective: bool = False,
                         cuts: dict | None = None) -> tuple[dict, list[dict], set[float]]:
    """Features, fills (both rules, both sides) and marks of one opportunity. Returns (opp row, fill rows, large-order times).

    Origin features use only the newest 500 prints before t (``visible_prints``); fills use ``post`` (ts > t, within the
    life). The stream for classifying in-life orders is visible-500 U post (item 5, ruling 1)."""
    t = o.t
    vis = visible_prints(prints_union(pre, {k: v[:0] for k, v in post.items()}, t) if prospective else pre, t)
    post_w = _take(post, (post["ts"] > t) & (post["ts"] <= t + max(o.life, 0.0) + MARK_S)) if len(post["ts"]) else post
    stream = prints_union(vis, post_w, t)
    orders = taker_orders(stream)
    flags = large_order_flags(orders["ts"].to_numpy(float), orders["notional"].to_numpy(float))
    ots = orders["ts"].to_numpy(float)
    n_vis_orders = int((ots < t).sum())
    classifiable = n_vis_orders >= D.B["large_order_min_prior"]
    larges = ots[flags == 1.0]
    after = larges[larges > t]
    life_end = t + o.life
    t_cancel = float(after[after < life_end][0]) if (after < life_end).any() else math.inf
    vo = orders[(orders["ts"] >= t - D.B["activity_window_s"]) & (orders["ts"] < t)]
    activity = int(len(vo))
    rt = round_trip_share(vis, t, truncated=o.truncated if o.pre_truncated is None else o.pre_truncated,
                          oldest_ts=o.oldest_ts if o.pre_truncated is None else o.pre_oldest)
    spread = o.ask - o.bid
    mid = (o.ask + o.bid) / 2.0
    lf_t = life_fraction(t, o.created, o.end)
    row = {
        "opp_id": o.opp_id, "market_id": o.market_id, "event": o.event, "dep": o.dep, "cat": category_key(o.cat), "t": t,
        "week": c1.iso_week(t), "day": pd.Timestamp(t, unit="s", tz="UTC").strftime("%Y-%m-%d"),
        "bid": o.bid, "ask": o.ask, "spread": spread, "mid": mid, "bid_size": o.bid_size, "ask_size": o.ask_size,
        "lf_t": lf_t, "classifiable": bool(classifiable), "t_cancel": t_cancel, "cancel_offset": t_cancel - t if math.isfinite(t_cancel) else math.nan,
        "activity": activity, "rt": rt, "abs_chg_24h": o.abs_chg_24h, "depth_bid_1c": o.depth_1c_own, "depth_ask_1c": o.depth_1c_ask, "depth_both": o.depth_1c_both,
        "taker_notional_24h": float(vo["notional"].sum()) if len(vo) else 0.0, "life_truncated": bool(o.life_truncated),
        "spread_band": _grid_band(spread, D.B["spread_bands"]), "price_band": _grid_band(mid, D.B["price_bands"]),
        "activity_tercile": (_grid_band(activity, cuts["activity_tercile_cuts"]) if cuts and cuts.get("activity_tercile_cuts") else -1),
    }
    hs = spread / 2.0
    fills: list[dict] = []
    for side, price, depth in (("bid", o.bid, o.bid_size), ("ask", o.ask, o.ask_size)):
        st = quote_fills(post_w, t, side, price, depth, life=o.life, truncated=o.truncated, oldest_ts=o.oldest_ts)
        for rule in RULES:
            status, tf = st[rule]
            row[f"{rule}_{side}_status"] = status
            row[f"{rule}_{side}_tfill"] = tf
            if status == -1:
                row[f"{rule}_{side}_wc_mo"] = _wc_for(marks, side, price, t + o.life, hs, after=t)
            if status != 1:
                continue
            fr = _fill_row(o, side, price, rule, tf, marks, hs, ots, flags, larges, prospective, post_w)
            fr["wc_mo"] = _wc_for(marks, side, price, tf + MARK_S, hs, after=tf)
            fills.append(fr)
    return row, fills, set(float(x) for x in larges)


def _wc_for(marks, side: str, price: float, t_limit: float, hs: float, after: float) -> float:
    fb, fa = marks.last_before(t_limit, hs, after) if marks is not None else (math.nan, math.nan)
    return worst_case_mo(side, price, fb, fa)


def _fill_row(o: Opp, side: str, price: float, rule: str, tf: float, marks, hs: float, ots, flags, larges, prospective: bool, post_w) -> dict:
    m6, _b6, _a6 = marks.mark(tf, MARK_S, hs) if marks is not None else (math.nan, math.nan, math.nan)
    m2, _b2, _a2 = marks.mark(tf, MARK2_S, hs) if marks is not None else (math.nan, math.nan, math.nan)
    reb = rebate_per_share(price, o.cat, fee_schedule=o.fee_schedule, fees_enabled=o.fees_enabled, prospective=prospective)
    reb_h = rebate_per_share(price, o.cat, fee_schedule=o.fee_schedule, fees_enabled=o.fees_enabled, prospective=prospective, halved=True)
    mo6 = mark_out(side, price, m6) if math.isfinite(m6) else math.nan
    mo2 = mark_out(side, price, m2) if math.isfinite(m2) else math.nan
    post_flags = {}
    for w_min in [D.B["post_window_s"] // 60, *D.B["w_sensitivity_min"]]:
        w = w_min * 60.0
        post_flags[w_min] = float(((larges >= tf - w) & (larges < tf)).any())
    n_prior = int((ots < tf).sum())
    return {"opp_id": o.opp_id, "market_id": o.market_id, "event": o.event, "dep": o.dep, "cat": category_key(o.cat), "side": side, "rule": rule,
            "t": o.t, "t_fill": tf, "price": price, "mark6": m6, "mo6": mo6, "mo2": mo2, "rebate": reb, "rebate_half": reb_h,
            "net6": mo6 + reb if math.isfinite(mo6) else math.nan, "net6_half": mo6 + reb_h if math.isfinite(mo6) else math.nan,
            "net2": mo2 + reb if math.isfinite(mo2) else math.nan, "mark_unavailable": not math.isfinite(m6),
            "lf": life_fraction(tf, o.created, o.end), "post": post_flags[D.B["post_window_s"] // 60],
            **{f"post{w}": post_flags[w] for w in D.B["w_sensitivity_min"]}, "classifiable_fill": bool(n_prior >= D.B["large_order_min_prior"]),
            "week": c1.iso_week(tf), "day": pd.Timestamp(tf, unit="s", tz="UTC").strftime("%Y-%m-%d"), "life_truncated": bool(o.life_truncated)}


# =============================================================================================
# 6. Estimator: expanding-past within-market slope, matched placebos
# =============================================================================================


def _dummies(s: pd.Series, prefix: str) -> pd.DataFrame:
    return pd.get_dummies(s.astype(str), prefix=prefix, drop_first=True, dtype=float)


def control_frame(df: pd.DataFrame, *, b5: bool = False) -> pd.DataFrame:
    """Controls (§CB3-B): entry spread, log(1 + touch depth, own side), |24h own-price change|, price-band and side
    dummies, category FE; B5 adds log(1 + depth both sides) and log(1 + taker notional 24h). Missing numeric controls are
    left NaN (those rows leave the regression; none is imputed)."""
    X = pd.DataFrame(index=df.index)
    X["spread"] = df["spread"].astype(float)
    X["log1p_depth_own"] = np.log1p(df["depth_own"].astype(float)) if "depth_own" in df else np.nan
    X["abs_chg_24h"] = df["abs_chg_24h"].astype(float).abs()
    X = X.join(_dummies(df["price_band"], "pb"))
    if "side" in df:
        X["side_ask"] = (df["side"] == "ask").astype(float)
    X = X.join(_dummies(df["cat"], "cat"))
    if b5:
        X["log1p_depth_both"] = np.log1p(df["depth_both"].astype(float))
        X["log1p_taker_notional_24h"] = np.log1p(df["taker_notional_24h"].astype(float))
    return X.loc[:, X.nunique(dropna=True) > 1]


def _fit_expanding(df: pd.DataFrame, regressor: str, controls: pd.DataFrame, target: str, *, order: str, ways: list[str], sign: int,
                   week_fe: bool, w: str | None = None, small_g: tuple[str, ...] = (), n_boot: int = 0, seed: int = D.SEED_BOOT) -> dict:
    d = pd.concat([df[["market_id", order, target, regressor, *ways]].reset_index(drop=True), controls.reset_index(drop=True)], axis=1)
    cols = [regressor, *controls.columns]
    dm = bd.expanding_demean(d, cols, by="market_id", order=order)
    Z = dm[list(controls.columns)].to_numpy(float) if len(controls.columns) else np.empty((len(dm), 0))
    if week_fe:
        wk = _dummies(df["week"].reset_index(drop=True), "wk").to_numpy(float)
        Z = np.column_stack([Z, wk]) if Z.size else wk
    res = C.slope_test(dm[target].to_numpy(float), dm[regressor].to_numpy(float), Z, {k: dm[k].to_numpy() for k in ways}, sign=sign,
                       w=None if w is None else df[w].reset_index(drop=True).to_numpy(float), small_g_ways=small_g, n_boot=n_boot, seed=seed)
    fin = np.isfinite(dm[target].to_numpy(float)) & np.isfinite(dm[regressor].to_numpy(float)) & (np.isfinite(Z).all(axis=1) if Z.size else True)
    res["n_markets_used"] = int(dm.loc[fin, "market_id"].nunique())
    res["n_markets_total"] = int(d["market_id"].nunique())
    return res


def _pooled_beta(df: pd.DataFrame, regressor: str, controls: pd.DataFrame, target: str, ways: list[str], week_fe: bool) -> float:
    Z = controls.to_numpy(float) if len(controls.columns) else np.empty((len(df), 0))
    if week_fe:
        wk = _dummies(df["week"].reset_index(drop=True), "wk").to_numpy(float)
        Z = np.column_stack([Z, wk]) if Z.size else wk
    r = C.slope_test(df[target].to_numpy(float), df[regressor].to_numpy(float), Z, {k: df[k].to_numpy() for k in ways}, sign=1,
                     n_boot=0, min_units=2, min_clusters=1)
    return float(r["beta"]) if r.get("testable") else math.nan


def within_between(df: pd.DataFrame, regressor: str, target: str) -> dict:
    """Pooled OLS of target on regressor split into the between-market slope (market means) and the within-market slope
    (full market demeaning); SB2 consequence 5."""
    d = df[["market_id", regressor, target]].dropna()
    if len(d) < 3:
        return {"between": None, "within": None}
    g = d.groupby("market_id")
    mx, my = g[regressor].transform("mean"), g[target].transform("mean")
    def slope(x, y):
        x, y = np.asarray(x, float), np.asarray(y, float)
        sxx = float(((x - x.mean()) ** 2).sum())
        return float(((x - x.mean()) * (y - y.mean())).sum() / sxx) if sxx > 1e-18 else None
    gm = d.groupby("market_id").agg(x=(regressor, "mean"), y=(target, "mean"))
    return {"between": slope(gm["x"], gm["y"]), "within": slope(d[regressor] - mx, d[target] - my), "pooled": slope(d[regressor], d[target])}


def mech_test(df: pd.DataFrame, regressor: str, *, tid: str, target: str = "net6", order: str = "t_fill", ways: list[str] | None = None,
              placebo_fn: Callable[[pd.DataFrame, int], pd.DataFrame] | None = None, draws: int = D.PLACEBO_DRAWS, week_fe: bool = False,
              b5: bool = False, small_g: tuple[str, ...] = (), n_boot: int = D.N_BOOT, weights: str | None = None) -> dict:
    """Mechanism test: J4-R's expanding-past within-market slope of ``target`` on ``regressor`` with controls (regressor and
    every control replaced by value minus the market's expanding mean over EARLIER rows; target raw; first row per market
    dropped), cluster ways with p = max (CB2 small-G rule for the UTC-day way), matched placebo and the J4-R reading rule.
    Reports beside it: the pooled slope, the draft's T = pooled - mean placebo pooled, and the within/between split."""
    spec = D.HYPOTHESES_CB3[tid]
    ways = ways or ["event", "dep", "day"]
    df = df.reset_index(drop=True)
    ctrl = control_frame(df, b5=b5)
    real = _fit_expanding(df, regressor, ctrl, target, order=order, ways=ways, sign=spec["sign"], week_fe=week_fe, w=None, small_g=small_g, n_boot=n_boot)
    out = {"tid": tid, **real, "effect": real.get("beta"), "estimator": "expanding_past_within_market"}
    if not real.get("testable"):
        out["family_status"] = "not testable"
        return out
    out["pooled_beta"] = _pooled_beta(df, regressor, ctrl, target, ways, week_fe)
    out["within_between"] = within_between(df, regressor, target)
    if weights is not None:
        wr = _fit_expanding(df, regressor, ctrl, target, order=order, ways=ways, sign=spec["sign"], week_fe=week_fe, w=weights, small_g=small_g, n_boot=0)
        out["weighted_beta"] = wr.get("beta")
    if placebo_fn is not None:
        betas, pooled = [], []
        for k in range(draws):
            dk = placebo_fn(df, D.SEED_PLACEBO + k).reset_index(drop=True)
            ck = control_frame(dk, b5=b5)
            r = _fit_expanding(dk, regressor, ck, target, order=order, ways=ways, sign=spec["sign"], week_fe=week_fe, small_g=small_g)
            betas.append(r["beta"] if r.get("testable") else math.nan)
            pooled.append(_pooled_beta(dk, regressor, ck, target, ways, week_fe))
        ps = C.placebo_summary(betas)
        rd = C.reading(ps, real["se"])
        ps.update(status=rd["status"])
        out["placebo"] = ps
        out["placebo_status"] = rd["status"]
        out["T_draft"] = out["pooled_beta"] - float(np.nanmean(pooled)) if np.isfinite(pooled).any() else None
    return out


def keeps_sign_and_floor(beta: float | None, floor: float, sign: int) -> bool:
    return bool(beta is not None and np.isfinite(beta) and sign * beta > 0 and sign * beta >= sign * floor)


def mech_advance(res: dict, tid: str, alpha: float, robust: dict[str, float | None]) -> dict:
    """Stage gate of a mechanism test: p < alpha in the declared direction, floor met by the point estimate, placebo read
    (family not void, no bias), and every binding robustness keeps sign and floor (``robust``: name -> re-estimated slope)."""
    spec = D.HYPOTHESES_CB3[tid]
    fails = []
    if not res.get("testable"):
        return {"advance": False, "fail": ["not_testable"]}
    if not res["p"] < alpha:
        fails.append("p")
    if not keeps_sign_and_floor(res["beta"], spec["floor"], spec["sign"]):
        fails.append("floor")
    st = res.get("placebo_status")
    if st is not None and st != "read":
        fails.append(f"placebo:{st}")
    for k, b in robust.items():
        if not keeps_sign_and_floor(b, spec["floor"], spec["sign"]):
            fails.append(f"robust:{k}")
    return {"advance": not fails, "fail": fails}


# ---- placebos -------------------------------------------------------------------------------------------------------


def placebo_circular_shift(fills: pd.DataFrame, large_times: dict[str, np.ndarray], spans: dict[str, tuple[float, float]], seed: int,
                           w_s: float = float(D.B["post_window_s"])) -> pd.DataFrame:
    """B1 placebo: shift each market's large-order time stream circularly by a uniform offset in [1 d, span - 1 d] (fills and
    fill prints untouched) and recompute ``post``. Markets with span < 2 d keep an offset of half the span."""
    rng = np.random.default_rng(seed)
    out = fills.copy()
    post = np.zeros(len(out))
    for mid, idx in out.groupby("market_id").indices.items():
        lt = np.asarray(large_times.get(mid, np.empty(0)), float)
        if not len(lt):
            continue
        lo, hi = spans[mid]
        span = max(hi - lo, 1.0)
        off = rng.uniform(DAY, span - DAY) if span > 2 * DAY else span / 2.0
        sh = np.sort(lo + np.mod(lt - lo + off, span))
        tf = out["t_fill"].to_numpy(float)[idx]
        a = np.searchsorted(sh, tf - w_s, side="left")
        b = np.searchsorted(sh, tf, side="left")
        post[idx] = (b > a).astype(float)
    out["post"] = post
    return out


def placebo_permute_within_market(df: pd.DataFrame, col: str, seed: int) -> pd.DataFrame:
    """B3 / B5 placebo: permute ``col`` within each market (keeps each market's multiset of values)."""
    rng = np.random.default_rng(seed)
    out = df.copy()
    vals = out[col].to_numpy(float).copy()
    for _mid, idx in out.groupby("market_id").indices.items():
        vals[idx] = vals[rng.permutation(idx)]
    out[col] = vals
    return out


# =============================================================================================
# 7. Economics: U baseline, filters, improvement rule, brackets
# =============================================================================================


def u_baseline(opps: pd.DataFrame, fills: pd.DataFrame, rule: str = "queue") -> dict:
    """Unfiltered maker U (cb3_descriptive): fill rate, mean mo, mean net per filled share, EV per quote, by side, price band,
    spread band and category."""
    f = fills[fills["rule"] == rule]
    n_opp = len(opps)
    fv = f[np.isfinite(f["net6"])]
    out = {"rule": rule, "n_quotes": int(n_opp), "n_fills": int(len(f)), "n_fills_marked": int(len(fv)),
           "fill_rate_per_side": float(len(f) / (2 * n_opp)) if n_opp else None,
           "mean_mo": float(fv["mo6"].mean()) if len(fv) else None, "mean_net": float(fv["net6"].mean()) if len(fv) else None,
           "ev_per_quote": float(fv["net6"].sum() / 2.0 / n_opp) if n_opp else None}
    mo = opps.set_index("opp_id")
    fj = fv.join(mo[["price_band", "spread_band"]], on="opp_id")
    out["by_side"] = {s: {"n": int(len(g)), "mean_net": float(g["net6"].mean())} for s, g in fv.groupby("side")}
    out["by_price_band"] = {str(k): {"n": int(len(g)), "mean_net": float(g["net6"].mean())} for k, g in fj.groupby("price_band")}
    out["by_spread_band"] = {str(k): {"n": int(len(g)), "mean_net": float(g["net6"].mean())} for k, g in fj.groupby("spread_band")}
    out["by_category"] = {str(k): {"n": int(len(g)), "mean_net": float(g["net6"].mean())} for k, g in fv.groupby("cat")}
    return out


def capacity(fills: pd.DataFrame, opps: pd.DataFrame, inclusion_prob: float = 1.0) -> dict:
    """Fills per day x 5 shares / inclusion probability, and the median displayed touch depth."""
    if not len(fills):
        return {"fills_per_day": 0.0, "shares_per_day": 0.0, "median_touch_depth": None}
    span = max((float(fills["t_fill"].max()) - float(fills["t_fill"].min())) / DAY, 1.0)
    d = np.r_[opps["bid_size"].to_numpy(float), opps["ask_size"].to_numpy(float)]
    d = d[np.isfinite(d)]
    return {"fills_per_day": len(fills) / span / inclusion_prob, "shares_per_day": len(fills) / span * OWN / inclusion_prob,
            "median_touch_depth": float(np.median(d)) if len(d) else None, "inclusion_prob": inclusion_prob}


def fill_wide(opps: pd.DataFrame, fills: pd.DataFrame, rule: str, net_col: str = "net6") -> pd.DataFrame:
    """Per-opportunity wide columns ``dt_bid/net_bid/dt_ask/net_ask`` (NaN if no fill with a mark) for vectorised filtered EV."""
    f = fills[(fills["rule"] == rule) & np.isfinite(fills[net_col])]
    out = opps[["opp_id"]].copy()
    for side in SIDES:
        g = f[f["side"] == side].drop_duplicates("opp_id").set_index("opp_id")
        out[f"dt_{side}"] = out["opp_id"].map(g["t_fill"] - g["t"])
        out[f"net_{side}"] = out["opp_id"].map(g[net_col])
    return out.set_index("opp_id")


def ev_per_opp(wide: pd.DataFrame, offset: np.ndarray, keep: np.ndarray | None = None) -> np.ndarray:
    """EV per quote (sum of kept fills' net x 5 / 10 = sum / 2) with the quote active for ``offset`` seconds after posting
    (a fill at or before the cancel time counts); ``keep`` False removes the quote (contributes 0, stays in the denominator)."""
    ev = np.zeros(len(wide))
    for side in SIDES:
        dt, nt = wide[f"dt_{side}"].to_numpy(float), wide[f"net_{side}"].to_numpy(float)
        ok = np.isfinite(dt) & (dt <= offset + 1e-9)
        ev += np.where(ok, nt, 0.0)
    ev = ev / 2.0
    return ev if keep is None else ev * keep


def strata_keys(opps: pd.DataFrame, *, extra_depth: bool = False) -> np.ndarray:
    cols = ["spread_band", "price_band", "cat", "activity_tercile"]
    key = opps[cols].astype(str).agg("|".join, axis=1)
    if extra_depth:
        dd = pd.qcut(opps["depth_both"].rank(method="first"), D.B["depth_deciles"], labels=False, duplicates="drop")
        key = key + "|d" + dd.astype(str)
    return key.to_numpy()


def draw_same_count(keys: np.ndarray, real: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Random mask with the same number of True per stratum as ``real``."""
    out = np.zeros(len(keys), bool)
    for k in np.unique(keys[real]):
        idx = np.flatnonzero(keys == k)
        n_real = int(real[idx].sum())
        out[rng.choice(idx, size=min(n_real, len(idx)), replace=False)] = True
    return out


def population(opps: pd.DataFrame, tid: str) -> pd.Series:
    if tid == "B2":
        return opps["classifiable"].astype(bool)
    if tid == "B4":
        return opps["lf_t"].notna()
    if tid == "B6":
        return opps["rt"].notna()
    raise ValueError(tid)


def real_filter(opps: pd.DataFrame, tid: str, cuts: dict | None) -> tuple[np.ndarray, np.ndarray]:
    """(offset, keep) of the declared filter on ``opps`` (offset seconds a quote stays active, keep False removes it)."""
    n = len(opps)
    if tid == "B2":
        off = opps["cancel_offset"].to_numpy(float)
        return np.where(np.isfinite(off), off, np.inf), np.ones(n, bool)
    if tid == "B4":
        return np.full(n, np.inf), ~(opps["lf_t"].to_numpy(float) >= D.B["lf_cut"])
    if tid == "B6":
        if not cuts or "rt_top_decile_cut" not in cuts:
            raise D.DeclarationError("B6 needs the frozen RT top-decile cut (committed spec frozen_cuts.rt_top_decile_cut)")
        return np.full(n, np.inf), opps["rt"].to_numpy(float) >= float(cuts["rt_top_decile_cut"])
    raise ValueError(tid)


def improvement_rule(opps_pop: pd.DataFrame, wide: pd.DataFrame, tid: str, cuts: dict | None, *, draws: int = D.RANDOM_FILTER_DRAWS,
                     pct: float = D.STAGE1_RANDOM_PCT, seed: int = D.SEED_RANDOM_FILTER) -> dict:
    """Binding improvement rule: the filtered maker's EV per quote (fixed U denominator, same population) minus U's, against
    the ``pct`` percentile of ``draws`` matched random filters acting in the filter's own units, within strata
    (spread band x price band x category x activity tercile; B6 also x depth decile)."""
    n = len(opps_pop)
    if n == 0:
        return {"testable": False}
    inf = np.full(n, np.inf)
    ev_u = float(ev_per_opp(wide, inf).sum() / n)
    off_r, keep_r = real_filter(opps_pop, tid, cuts)
    ev_f = float(ev_per_opp(wide, off_r, keep_r).sum() / n)
    keys = strata_keys(opps_pop, extra_depth=(tid == "B6"))
    rng = np.random.default_rng(seed)
    imps = np.empty(draws)
    if tid == "B2":
        cancelled = np.isfinite(off_r)
        for d in range(draws):
            chosen = draw_same_count(keys, cancelled, rng)
            off = np.full(n, np.inf)
            for k in np.unique(keys[cancelled]):
                idx_c = np.flatnonzero(chosen & (keys == k))
                pool = off_r[cancelled & (keys == k)]
                off[idx_c] = rng.choice(pool, size=len(idx_c))
            imps[d] = ev_per_opp(wide, off).sum() / n - ev_u
    elif tid == "B4":
        removed = ~keep_r
        for d in range(draws):
            rem = draw_same_count(keys, removed, rng)
            imps[d] = ev_per_opp(wide, inf, ~rem).sum() / n - ev_u
    else:
        for d in range(draws):
            sel = draw_same_count(keys, keep_r, rng)
            imps[d] = ev_per_opp(wide, inf, sel).sum() / n - ev_u
    thr = float(np.percentile(imps, pct))
    real = ev_f - ev_u
    return {"testable": True, "ev_u": ev_u, "ev_filtered": ev_f, "improvement": real, "random_pct": pct, "random_threshold": thr,
            "random_mean": float(imps.mean()), "passes": bool(real > thr), "n_population": int(n), "n_draws": draws}


def filtered_fills(fills: pd.DataFrame, opps_pop: pd.DataFrame, tid: str, cuts: dict | None, rule: str = "queue") -> pd.DataFrame:
    """Fills of the filtered maker among the population: B2 keeps a fill at or before the first large order after posting,
    B4 drops quotes with LF(t) >= 0.90, B6 keeps top-decile RT quotes."""
    f = fills[(fills["rule"] == rule) & fills["opp_id"].isin(opps_pop["opp_id"])]
    o = opps_pop.set_index("opp_id")
    off, keep = real_filter(opps_pop, tid, cuts)
    offs = pd.Series(off, index=o.index)
    keeps = pd.Series(keep, index=o.index)
    f = f[f["opp_id"].map(keeps).astype(bool)]
    f = f[(f["t_fill"] - f["t"]) <= f["opp_id"].map(offs) + 1e-9]
    return f


def worst_case_rows(opps_pop: pd.DataFrame, fills_kept: pd.DataFrame, tid: str, cuts: dict | None, rule: str = "queue") -> np.ndarray:
    """Worst-case nets added by the binding bracket: (a) per quote with an unavailable fill status on any side, only the side
    with the lower mark-out fills (far touch, no rebate); (b) every kept fill with an unavailable mark at its worst-case
    mark-out (no rebate)."""
    off, keep = real_filter(opps_pop, tid, cuts)
    o = opps_pop.reset_index(drop=True)
    add = []
    for side in SIDES:
        st = o[f"{rule}_{side}_status"].to_numpy()
        wc = o.get(f"{rule}_{side}_wc_mo", pd.Series(np.nan, index=o.index)).to_numpy(float)
        o[f"_u_{side}"] = np.where((st == -1) & keep, wc, np.nan)
    both = np.fmin(o["_u_bid"].to_numpy(float), o["_u_ask"].to_numpy(float)) if len(o) else np.empty(0)
    add.extend([x for x in both if np.isfinite(x)])
    mu = fills_kept[fills_kept["mark_unavailable"]]
    add.extend(list(mu["wc_mo"].to_numpy(float)))
    return np.asarray([x for x in add if np.isfinite(x)], float)


def econ_test(opps: pd.DataFrame, fills: pd.DataFrame, tid: str, *, cuts: dict | None, stage: int, weights: str | None = None,
              draws: int = D.RANDOM_FILTER_DRAWS, n_boot: int = D.N_BOOT, small_g: tuple[str, ...] = (), ways: list[str] | None = None,
              compare_u: bool = True) -> dict:
    """Economic test B2 / B4 / B6 (and the A3 machinery): mean net per filled share of the filtered maker, one-sided > 0, with
    the floor, EV per quote > 0 over the fixed U denominator, the binding improvement rule and the binding brackets:
    top-5 clusters dropped, weighted sign, touch-rule sign, rebate halved (floor and sign), residual-unavailable worst case."""
    spec = D.HYPOTHESES_CB3[tid]
    alpha = D.ALPHA_STAGE1 if stage == 1 else D.ALPHA_STAGE2
    pct = D.STAGE1_RANDOM_PCT if stage == 1 else D.STAGE2_RANDOM_PCT
    ways = ways or (["event", "dep"] if stage == 1 else ["event", "dep", "day"])
    sg = small_g if stage != 1 else ()
    pop_mask = population(opps, tid)
    pop = opps[pop_mask].reset_index(drop=True)
    out: dict = {"tid": tid, "stage": stage, "n_population": int(len(pop))}
    fk = filtered_fills(fills, pop, tid, cuts, "queue")
    fkv = fk[np.isfinite(fk["net6"])]
    out["n_fills"], out["n_fills_marked"] = int(len(fk)), int(len(fkv))
    cl = {k: fkv[k].to_numpy() for k in ways}
    mt = C.mean_test(fkv["net6"].to_numpy(float), cl, sign=1, small_g_ways=sg, n_boot=n_boot)
    out.update(testable=mt["testable"], p=mt["p"], effect=mt["mean"], ci95=mt.get("ci95"), n=mt["n"], clusters=mt.get("clusters"), reason=mt.get("reason"))
    wide_q = fill_wide(pop, fills, "queue")
    n = len(pop)
    off, keep = real_filter(pop, tid, cuts) if n else (np.empty(0), np.empty(0, bool))
    ev = float(ev_per_opp(wide_q, off, keep).sum() / n) if n else math.nan
    out["ev_per_quote"] = ev
    if compare_u:
        out["improvement"] = improvement_rule(pop, wide_q, tid, cuts, draws=draws, pct=pct)
    if not mt["testable"]:
        out.update(advance=False, fail=["not_testable"])
        return out
    fail = []
    if not mt["p"] < alpha:
        fail.append("p")
    if not mt["mean"] >= spec["floor"]:
        fail.append("floor")
    if not ev > 0:
        fail.append("ev_per_quote")
    if compare_u and not out["improvement"].get("passes"):
        fail.append("improvement_rule")
    # binding brackets
    br: dict = {}
    for k in ways:
        keepm = C.top_clusters_mask(fkv["net6"].to_numpy(float) - mt["mean"], fkv[k].to_numpy())
        v = fkv.loc[keepm, "net6"].to_numpy(float)
        br[f"top5_{k}"] = float(v.mean()) if len(v) else None
        if not (len(v) and v.mean() >= spec["floor"]):
            fail.append(f"robust:top5_{k}")
    if weights is not None and weights in fkv:
        wv = fkv[weights].to_numpy(float)
        wm = float((wv * fkv["net6"].to_numpy(float)).sum() / wv.sum())
        br["weighted_mean"] = wm
        if not wm > 0:
            fail.append("robust:weighted_sign")
    ft = filtered_fills(fills, pop, tid, cuts, "touch")
    ftv = ft[np.isfinite(ft["net6"])]
    br["touch_rule_mean"] = float(ftv["net6"].mean()) if len(ftv) else None
    if not (len(ftv) and ftv["net6"].mean() > 0):
        fail.append("robust:touch_rule_sign")
    h = fkv["net6_half"].to_numpy(float)
    hm = float(h.mean()) if len(h) else math.nan
    hev = float((h.sum() / 2.0) / n) if n else math.nan
    br["rebate_half_mean"], br["rebate_half_ev"] = hm, hev
    if not (hm >= spec["floor"] and hev > 0):
        fail.append("robust:rebate_halved")
    wc = worst_case_rows(pop, fkv, tid, cuts, "queue")
    allv = np.r_[fkv["net6"].to_numpy(float), wc]
    br["worst_case_mean"], br["worst_case_added"] = float(allv.mean()) if len(allv) else None, int(len(wc))
    if not (len(allv) and allv.mean() > 0):
        fail.append("robust:worst_case_unavailable")
    out["brackets"] = br
    out["advance"] = not fail
    out["fail"] = fail
    return out


# =============================================================================================
# 8. Unit assembly from a history market stream
# =============================================================================================


def history_market_units(rec: dict, books_m: pd.DataFrame, ts_p: np.ndarray | None, vals_p: np.ndarray | None, tr: pd.DataFrame | None,
                         truncated: bool, oldest_ts, ctx: c1.Ctx, cuts: dict | None, dep: str | None = None, weight: float = 1.0,
                         with_marks: bool = True) -> tuple[list[dict], list[dict], set[float], tuple[float, float] | None, dict]:
    """Quote opportunities, fills and large-order times of one history market at its pmxt 6h-grid books (both book clocks <= t).
    Population: binary, open, traded before t (unavailable if unknown: leaves the population, counted), end_at > t + 8h,
    eligible book. Returns (opp rows, fill rows, large times, (first, last) print ts, diag). ``with_marks`` False (census)
    builds no marks and reads no price series: every mark-dependent field stays NaN."""
    pr = prints_arrays(tr)
    diag = {"origins": 0, "not_eligible_book": 0, "not_open": 0, "end_too_close": 0, "trade_state_unavailable": 0, "no_prior_trade": 0, "kept": 0}
    rows, frows, larges = [], [], set()
    marks = HistoryMarks(ts_p, vals_p) if (with_marks and ts_p is not None) else None
    cat = category_key(rec.get("fee_category"))
    old = c1.oldest_or_inf(oldest_ts) if truncated else None
    closed_early = bool(math.isfinite(rec["close_epoch"]) and math.isfinite(rec["end_epoch"]) and rec["close_epoch"] < rec["end_epoch"] - DAY)
    bk = books_m[(books_m["state"] == "two_sided")].sort_values("origin_ts")
    bt = bk["origin_ts"].to_numpy(float)
    bmid = ((bk["sw_best_bid"] + bk["sw_best_ask"]) / 2.0).to_numpy(float)
    bsp = (bk["sw_best_ask"] - bk["sw_best_bid"]).to_numpy(float)
    for b in bk.itertuples():
        diag["origins"] += 1
        t = float(b.origin_ts)
        bid, ask = float(b.sw_best_bid), float(b.sw_best_ask)
        if not eligible_quote(bid, ask):
            diag["not_eligible_book"] += 1
            continue
        if not bool(c1.open_at(rec["created_epoch"], rec["close_epoch"], np.array([t]))[0]):
            diag["not_open"] += 1
            continue
        if not (rec["end_epoch"] > t + D.MAKER["end_at_margin_s"]):
            diag["end_too_close"] += 1
            continue
        st = int(c1.trade_condition_state(pr["ts"], truncated, old, -np.inf, t, 1)[0])
        if st == -1:
            diag["trade_state_unavailable"] += 1
            continue
        if st == 0:
            diag["no_prior_trade"] += 1
            continue
        chg = math.nan
        if with_marks and ts_p is not None and len(ts_p):
            pp = c1.asof_quote(ts_p, vals_p, np.array([t, t - DAY]))
            chg = abs(float(pp[0] - pp[1])) if np.isfinite(pp).all() else math.nan
        bs, as_ = float(getattr(b, "sw_bid_size_1", math.nan)), float(getattr(b, "sw_ask_size_1", math.nan))
        db, da = float(getattr(b, "sw_depth_bid_1c", math.nan)), float(getattr(b, "sw_depth_ask_1c", math.nan))  # 1c depth (pmxt); touch size if absent
        d_both = (db + da) if (math.isfinite(db) and math.isfinite(da)) else ((bs if math.isfinite(bs) else 0.0) + (as_ if math.isfinite(as_) else 0.0))
        o = Opp(opp_id=f"{rec['market_id']}@{int(t)}", market_id=rec["market_id"], event=rec["event_id"], dep=dep or rec["event_id"], cat=cat, t=t,
                bid=bid, ask=ask, bid_size=bs, ask_size=as_, created=rec["created_epoch"], end=rec["end_epoch"], abs_chg_24h=chg,
                depth_1c_own=db if math.isfinite(db) else bs, depth_1c_ask=da if math.isfinite(da) else as_, depth_1c_both=d_both, truncated=truncated, oldest_ts=old)
        row, fl, lg = evaluate_opportunity(o, pr, pr, marks, prospective=False, cuts=cuts)
        row.update(w=weight, closed_early=closed_early, book_age_s=float(getattr(b, "sw_book_age_s", math.nan)))
        for f in fl:
            f.update(w=weight, closed_early=closed_early)
            # pmxt book-mid mark check (ruling 4): first two-sided spread <= 0.10 grid origin >= t_fill + 4h
            j = int(np.searchsorted(bt, f["t_fill"] + float(D.MAKER["history_pmxt_mark_check_s"]), side="left"))
            lim = f["t_fill"] + float(D.MAKER["history_pmxt_mark_check_s"]) + 6 * HOUR  # one 6h grid step: the search is bounded
            while j < len(bt) and bt[j] <= lim and not bsp[j] <= D.MAKER["spread_max"] + 1e-12:
                j += 1
            if with_marks and j < len(bt) and bt[j] <= lim and bsp[j] <= D.MAKER["spread_max"] + 1e-12:
                f["mark_pmxt"] = float(bmid[j])
                f["net_pmxt"] = mark_out(f["side"], f["price"], float(bmid[j])) + f["rebate"]
            else:
                f["mark_pmxt"], f["net_pmxt"] = math.nan, math.nan
        rows.append(row)
        frows.extend(fl)
        larges |= lg
        diag["kept"] += 1
    span = (float(pr["ts"][0]), float(pr["ts"][-1])) if len(pr["ts"]) else None
    return rows, frows, larges, span, diag


def attach_fill_features(fills: pd.DataFrame, opps: pd.DataFrame) -> pd.DataFrame:
    """Merge opportunity columns needed by the mechanism controls onto fills (``depth_own`` is the own-side touch size)."""
    if not len(fills):
        return fills
    o = opps.set_index("opp_id")
    f = fills.join(o[["spread", "mid", "abs_chg_24h", "price_band", "spread_band", "depth_both", "taker_notional_24h", "bid_size", "ask_size", "depth_bid_1c", "depth_ask_1c", "classifiable", "lf_t", "rt", "t_cancel"]], on="opp_id")
    f["depth_own"] = np.where(f["side"] == "bid", f["depth_bid_1c"], f["depth_ask_1c"])  # own side, 1c depth
    return f


def opp_level_frame(opps: pd.DataFrame, fills: pd.DataFrame, rule: str = "queue") -> pd.DataFrame:
    """B5 frame: one row per quote opportunity with RT defined; ``ev_quote`` = sum of marked net over its fills / 2 (0 if none)."""
    f = fills[(fills["rule"] == rule) & np.isfinite(fills["net6"])].groupby("opp_id")["net6"].sum()
    o = opps[opps["rt"].notna()].copy()
    o["ev_quote"] = o["opp_id"].map(f).fillna(0.0) / 2.0
    o["depth_own"] = o["depth_bid_1c"]
    o["t_fill"] = o["t"]
    return o


# =============================================================================================
# 9. Prospective layout reader (cb3_followup/)
# =============================================================================================


class FollowupReader:
    """Reads ``cb3_followup/<pass>/{pre,post,vacuum}/trades.csv.gz`` (history-backfill trade layout plus ``market_id``) and
    ``cb3_followup/<pass>/meta.json`` (``request_utc``; ``page_cap_markets``). Layout assumption documented in the
    implementation notes: the follow-up step is a separate deliverable."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def meta(self, pass_id: str) -> dict:
        p = self.root / pass_id / "meta.json"
        return json.loads(p.read_text()) if p.exists() else {}

    def trades(self, pass_id: str, part: str, market_id: str) -> dict[str, np.ndarray]:
        """``pass_id`` = the capture id of the follow-up pass (i + 1) for opportunities of pass i. ``pre`` reads the copied
        ``wallets.csv.gz`` (hashed wallets, same rows as the trade sample), ``post`` / ``vacuum`` their ``trades.csv.gz``."""
        p = self.root / pass_id / part / ("wallets.csv.gz" if part == "pre" else "trades.csv.gz")
        if not p.exists():
            return prints_arrays(None)
        df = pd.read_csv(p, dtype={"market_id": str, "wallet_hash": str, "trade_key": str})
        return prints_arrays(df[df["market_id"].astype(str) == str(market_id)])


# =============================================================================================
# 10. History pipeline (h2_main trades + pmxt book table): census and Stage 1 screen
# =============================================================================================

MARK_COLS = ("mark6", "mo6", "mo2", "net6", "net2", "net6_half", "wc_mo", "mark_pmxt", "net_pmxt")


def assert_no_marks(df: pd.DataFrame) -> None:
    """Census guard: no mark, mark-out, net or T-capture column may be reachable from a census frame."""
    bad = [c for c in df.columns if c in D.CENSUS_FORBIDDEN_COLUMNS or c in MARK_COLS or "_wc_mo" in c]
    if bad:
        raise D.Cb3Error(f"census frame carries forbidden columns {bad}")


def _iter_history(run_dir: Path, frame: pd.DataFrame, ids: set[str], need_prices: bool):
    from . import history_backfill as hb

    run_dir = Path(run_dir)
    prog = hb._read_progress(run_dir / "progress.jsonl")
    for r in frame.to_dict("records"):
        mid = str(r["market_id"])
        if mid not in ids:
            continue
        p = prog.get(mid)
        if not p or p.get("status") != "done":
            continue
        tp = run_dir / "trades" / f"{mid}.csv.gz"
        pp = run_dir / "prices" / f"{mid}.csv.gz"
        if not tp.exists() or (need_prices and not pp.exists()):
            continue
        ts, vals = hb.load_prices(pp) if need_prices else (None, None)
        yield c1.norm_rec(r), ts, vals, hb.load_trades(tp), bool(p.get("trades_truncated")), p.get("trades_oldest_ts")


def history_units(run_dir: Path, books_path: Path, *, cuts: dict | None = None, with_marks: bool = True, max_markets: int | None = None) -> dict:
    """Build the opportunity and fill tables of the h2 history screen. Refuses the reserved run ids. The census calls this with
    ``with_marks=False`` (no price series is even read)."""
    run_dir = Path(run_dir)
    D.refuse_run_id(run_dir.name)
    c1.forbid_run(run_dir.name)
    ctx = c1.make_ctx(run_dir)
    frame = c1.load_sample(run_dir, census=True)
    wmap = dict(zip(frame["market_id"].astype(str), frame["sample_weight"].astype(float), strict=True)) if "sample_weight" in frame else {}
    books = c1.load_books(books_path)
    books = books[books["state"] == "two_sided"]
    depmap: dict[str, str] = {}
    pan = run_dir / "panel_H2h.csv.gz"
    if pan.exists():
        pdf = pd.read_csv(pan, usecols=["market_id", "dep_group"], dtype={"market_id": str}).dropna()
        depmap = pdf.drop_duplicates("market_id").set_index("market_id")["dep_group"].astype(str).to_dict()
    ids = set(books["market_id"].astype(str))
    rows, frows, larges, spans = [], [], {}, {}
    diag: dict[str, int] = {}
    n = 0
    for rec, ts_p, vals_p, tr, trunc, oldest in _iter_history(run_dir, frame, ids, need_prices=with_marks):
        bm = books[books["market_id"].astype(str) == rec["market_id"]]
        r, f, lg, span, d = history_market_units(rec, bm, ts_p, vals_p, tr, trunc, oldest, ctx, cuts, dep=depmap.get(rec["market_id"]),
                                                 weight=wmap.get(rec["market_id"], 1.0), with_marks=with_marks)
        rows += r
        frows += f
        for k, v in d.items():
            diag[k] = diag.get(k, 0) + v
        if lg:
            larges[rec["market_id"]] = np.array(sorted(lg))
        if span is not None:
            spans[rec["market_id"]] = span
        n += 1
        if max_markets and n >= max_markets:
            break
    opps, fills = pd.DataFrame(rows), pd.DataFrame(frows)
    return {"opps": opps, "fills": fills, "large_times": larges, "spans": spans, "diag": diag, "n_markets": n, "ctx": ctx}


def scope_split(opps: pd.DataFrame, fills: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """CATEGORY_SCOPE 'non_sports': counted tests use non-sports units; sports units are a cb3_descriptive stratum."""
    sp_o = opps["cat"].map(c1.is_sports) if len(opps) else pd.Series(dtype=bool)
    ids = set(opps.loc[sp_o, "opp_id"]) if len(opps) else set()
    sp_f = fills["opp_id"].isin(ids) if len(fills) else pd.Series(dtype=bool)
    return opps[~sp_o], fills[~sp_f], opps[sp_o], fills[sp_f]


def _lf_dist(fills: pd.DataFrame) -> dict:
    v = fills["lf"].dropna().to_numpy(float)
    return {"n": int(len(v)), "deciles": [float(x) for x in np.percentile(v, np.arange(0, 101, 10))] if len(v) else None}


def _expanding_counts(df: pd.DataFrame) -> dict:
    g = df.groupby("market_id").size()
    return {"rows": int(len(df)), "markets": int(len(g)), "markets_ge2": int((g >= 2).sum()), "rows_usable": int(g[g >= 2].sum() - (g >= 2).sum())}


def census_history(run_dir: Path, books_path: Path, *, max_markets: int | None = None) -> dict:
    """q0061 history part: counts only. No mark, mark-out, net, EV or any price after a fill is computed or reachable."""
    u = history_units(run_dir, books_path, with_marks=False, max_markets=max_markets)
    opps, fills = u["opps"], u["fills"]
    if len(opps):
        opps = opps.drop(columns=[c for c in opps.columns if c.endswith("_wc_mo")])
    if len(fills):
        fills = fills.drop(columns=[c for c in MARK_COLS if c in fills.columns])
    assert_no_marks(opps)
    assert_no_marks(fills)
    cnt = {"n_markets_read": u["n_markets"], "exclusions": u["diag"], "n_quote_opportunities_all": int(len(opps))}
    if not len(opps):
        return {**cnt, "note": "no opportunities"}
    o_ns, f_ns, o_sp, _f_sp = scope_split(opps, fills)
    cnt["n_quote_opportunities_non_sports"], cnt["n_quote_opportunities_sports_stratum"] = int(len(o_ns)), int(len(o_sp))
    cnt["fills"] = {f"{r}_{s}": {"filled": int(((fills["rule"] == r) & (fills["side"] == s)).sum()),
                                 "unavailable_quotes": int((opps[f"{r}_{s}_status"] == -1).sum())} for r in RULES for s in SIDES}
    cnt["classifiable_share"] = float(o_ns["classifiable"].mean()) if len(o_ns) else None
    q = f_ns[f_ns["rule"] == "queue"]
    cnt["fills_queue_non_sports"] = int(len(q))
    cnt["fills_with_large_order_prior_30min"] = int(q["post"].sum()) if len(q) else 0
    cnt["fills_classifiable"] = int(q["classifiable_fill"].sum()) if len(q) else 0
    cnt["life_fraction_of_fills"] = _lf_dist(q)
    rt = o_ns["rt"].dropna().to_numpy(float)
    act = o_ns["activity"].to_numpy(float)
    cnt["rt_defined_opportunities"] = int(len(rt))
    cnt["frozen_cuts_proposal"] = {"rt_top_decile_cut": float(np.quantile(rt, D.B["rt_top_quantile"])) if len(rt) else None,
                                   "activity_tercile_cuts": [float(x) for x in np.percentile(act, [100 / 3, 200 / 3])] if len(act) else None,
                                   "basis": "all non-sports quote opportunities of the history census; pin in the committed spec before any screen"}
    fa = attach_fill_features(q, o_ns)
    cnt["expanding_estimator_counts"] = {
        "B1": _expanding_counts(fa[fa["classifiable"].astype(bool)]) if len(fa) else None,
        "B3": _expanding_counts(fa[fa["lf"].notna()]) if len(fa) else None,
        "B5": _expanding_counts(o_ns[o_ns["rt"].notna()]) if len(o_ns) else None}
    cnt["clusters"] = {"event": int(o_ns["event"].nunique()), "dep": int(o_ns["dep"].nunique()), "day": int(o_ns["day"].nunique())}
    cnt["dep_fallback_share"] = float((o_ns["dep"] == o_ns["event"]).mean()) if len(o_ns) else None  # share on the event-id fallback (no panel dep_group)
    cnt["population_sizes"] = {"B2": int(population(o_ns, "B2").sum()), "B4": int(population(o_ns, "B4").sum()), "B6": int(population(o_ns, "B6").sum())}
    return cnt


def _robust_slope(df: pd.DataFrame, regressor: str, tid: str, *, target: str, ways: list[str], week_fe: bool, b5: bool = False, order: str = "t_fill") -> float | None:
    r = mech_test(df, regressor, tid=tid, target=target, order=order, ways=ways, week_fe=week_fe, b5=b5, n_boot=0, placebo_fn=None)
    return r.get("beta") if r.get("testable") else None


def _top5_drop(df: pd.DataFrame, regressor: str, target: str, way: str, order: str) -> pd.DataFrame:
    d = df.reset_index(drop=True)
    dm = bd.expanding_demean(d[["market_id", order, regressor]].assign(_y=d[target]), [regressor], by="market_id", order=order)
    contrib = (dm[regressor].fillna(0.0) * (d[target] - d[target].mean())).to_numpy(float)
    return d[C.top_clusters_mask(contrib, d[way].to_numpy())]


def mech_stage(df: pd.DataFrame, tid: str, regressor: str, *, ways: list[str], small_g: tuple[str, ...], stage: int, history: bool, n_boot: int, draws: int,
               placebo_fn, week_fe: bool = False, b5: bool = False, order: str = "t_fill", target: str = "net6", extra_robust: dict[str, pd.DataFrame] | None = None) -> dict:
    """One mechanism test with its binding robustness and advance decision."""
    alpha = D.ALPHA_STAGE1 if stage == 1 else D.ALPHA_STAGE2
    res = mech_test(df, regressor, tid=tid, target=target, order=order, ways=ways, placebo_fn=placebo_fn, draws=draws, week_fe=week_fe, b5=b5,
                    small_g=small_g, n_boot=n_boot, weights="w" if "w" in df else None)
    robust: dict[str, float | None] = {}
    if res.get("testable"):
        for way in [w for w in ways if w != "day"]:
            robust[f"top5_{way}"] = _robust_slope(_top5_drop(df, regressor, target, way, order), regressor, tid, target=target, ways=ways, week_fe=week_fe, b5=b5, order=order)
        if history and "net_pmxt" in df and tid in ("B1", "B3"):
            sub = df[df["net_pmxt"].notna()]
            robust["pmxt_mark"] = _robust_slope(sub, regressor, tid, target="net_pmxt", ways=ways, week_fe=week_fe, b5=b5, order=order)
        if not history and "net_wc" in df:
            robust["worst_case_mark"] = _robust_slope(df, regressor, tid, target="net_wc", ways=ways, week_fe=week_fe, b5=b5, order=order)
        if not history and "life_truncated" in df:
            robust["untruncated_life"] = _robust_slope(df[~df["life_truncated"].astype(bool)], regressor, tid, target=target, ways=ways, week_fe=week_fe, b5=b5, order=order)
        if history and tid == "B3" and "closed_early" in df:
            robust["lookahead_drop"] = _robust_slope(df[~df["closed_early"].astype(bool)], regressor, tid, target=target, ways=ways, week_fe=week_fe, b5=b5, order=order)
        for k, sub in (extra_robust or {}).items():
            robust[k] = _robust_slope(sub, regressor, tid, target=target, ways=ways, week_fe=week_fe, b5=b5, order=order)
        wb = res.get("weighted_beta")
        if wb is not None and not C.sign_agree(wb, res["beta"]):
            robust["weighted_sign"] = None
    adv = mech_advance(res, tid, alpha, robust) if res.get("testable") else {"advance": False, "fail": ["not_testable"]}
    res.update(robust=robust, advance=adv["advance"], fail=adv["fail"])
    res["entry_exception_stage2"] = bool(not res.get("testable") and stage == 1)
    return res


def screen_history(run_dir: Path, books_path: Path, cuts: dict, *, n_boot: int = D.N_BOOT, placebo_draws: int = D.PLACEBO_DRAWS,
                   random_draws: int = D.RANDOM_FILTER_DRAWS, max_markets: int | None = None, stage: int = 1) -> dict:
    """Stage 1 on h2_main + the pmxt book table: B1-B6 against the unfiltered maker U (reported). Seeded by HB2 F3/F7 on the same trades
    (L1, a stop rule). Returns the results document (no files written)."""
    u = history_units(run_dir, books_path, cuts=cuts, with_marks=True, max_markets=max_markets)
    opps, fills = u["opps"], u["fills"]
    out: dict = {"stage": stage, "dataset": Path(run_dir).name, "n_markets": u["n_markets"], "exclusions": u["diag"], "tests": {}, "placebo": {}, "descriptive": {}}
    if not len(opps):
        out["note"] = "no quote opportunities"
        return out
    o_ns, f_ns, o_sp, f_sp = scope_split(opps, fills)
    out["descriptive"]["U_non_sports"] = u_baseline(o_ns, f_ns)
    out["descriptive"]["U_sports_stratum"] = u_baseline(o_sp, f_sp) if len(o_sp) else {"n_quotes": 0}
    out["descriptive"]["capacity"] = capacity(f_ns[f_ns["rule"] == "queue"], o_ns)
    out["descriptive"]["book_age_sensitivity"] = _book_age(o_ns, f_ns)
    ways = ["event", "dep"]
    q = attach_fill_features(f_ns[(f_ns["rule"] == "queue")], o_ns)
    qm = q[np.isfinite(q["net6"])].copy()
    qm["net_wc"] = qm["net6"]
    # B1
    b1 = qm[qm["classifiable"].astype(bool)]
    out["tests"]["B1"] = mech_stage(b1, "B1", "post", ways=ways, small_g=(), stage=stage, history=True, n_boot=n_boot, draws=placebo_draws,
                                    placebo_fn=lambda d, s: placebo_circular_shift(d, u["large_times"], u["spans"], s))
    out["tests"]["B1"]["w_sensitivity_min_reported"] = {w: _robust_slope(b1.assign(post=b1[f"post{w}"]), "post", "B1", target="net6", ways=ways, week_fe=False)
                                                       for w in D.B["w_sensitivity_min"]} if len(b1) else {}
    # B3
    b3 = qm[qm["lf"].notna()]
    out["tests"]["B3"] = mech_stage(b3, "B3", "lf", ways=ways, small_g=(), stage=stage, history=True, n_boot=n_boot, draws=placebo_draws,
                                    placebo_fn=lambda d, s: placebo_permute_within_market(d, "lf", s), week_fe=True)
    # B5
    b5 = opp_level_frame(o_ns, f_ns)
    b5["w"] = o_ns.set_index("opp_id")["w"].reindex(b5["opp_id"]).to_numpy()
    out["tests"]["B5"] = mech_stage(b5, "B5", "rt", ways=ways, small_g=(), stage=stage, history=True, n_boot=n_boot, draws=placebo_draws, b5=True,
                                    placebo_fn=lambda d, s: placebo_permute_within_market(d, "rt", s), order="t_fill", target="ev_quote")
    for tid in ("B2", "B4", "B6"):
        out["tests"][tid] = econ_test(o_ns, f_ns[f_ns["rule"].isin(RULES)], tid, cuts=cuts, stage=stage, weights="w", draws=random_draws, n_boot=n_boot, ways=ways)
        out["tests"][tid]["entry_exception_stage2"] = bool(not out["tests"][tid].get("testable") and stage == 1)
    u_mean = out["descriptive"]["U_non_sports"].get("mean_net")
    adv_any = any(t.get("advance") for t in out["tests"].values())
    out["family_verdict_flag"] = ("U mean net below -1.5c with no filter advancing: dominated by adverse selection in every identifiable state"
                                 if (u_mean is not None and u_mean < -0.015 and not adv_any) else None)
    for tid, t in out["tests"].items():
        if "placebo" in t:
            out["placebo"][tid] = t["placebo"]
    return out


def _book_age(opps: pd.DataFrame, fills: pd.DataFrame) -> dict:
    if "book_age_s" not in opps or not opps["book_age_s"].notna().any():
        return {"available": False}
    ok = set(opps.loc[~(opps["book_age_s"] > 3600.0), "opp_id"])
    f = fills[(fills["rule"] == "queue") & fills["opp_id"].isin(ok) & np.isfinite(fills["net6"])]
    return {"available": True, "n_quotes_kept": len(ok), "n_fills": int(len(f)), "mean_net": float(f["net6"].mean()) if len(f) else None}


# =============================================================================================
# 11. Prospective pipeline (quote_state/ sweeps + cb3_followup/ prints): census and Stage 2 / P
# =============================================================================================


def _traded_before(P, j: int, m: int) -> bool:
    ltp, vol = P.mat["last_trade_price"][m, j], P.mat["volume_num"][m, j]
    return bool(np.isfinite(ltp) and not (np.isfinite(vol) and vol <= 0))


def _pass_aligned(d: Path, previous_cap: str) -> tuple[bool, str]:
    """The follow-up dir of pass j+1 must be a recorded pass (manifest complete / incomplete) built for capture j."""
    try:
        man = json.loads((d / "manifest.json").read_text())
        plan = json.loads((d / "plan.json").read_text())
    except (OSError, ValueError):
        return False, "missing"
    if man.get("state") not in ("complete", "incomplete"):
        return False, f"state_{man.get('state')}"
    if plan.get("previous_capture_id") != previous_cap:
        return False, "misaligned"
    if not (d / "pre" / "wallets.csv.gz").exists():
        return False, "no_pre"
    return True, "ok"


def build_prospective(P, reader: FollowupReader, *, with_marks: bool = True, origin_before: float | None = None, cuts: dict | None = None) -> dict:
    """Quote opportunities and fills of the follow-up subsample. For pass j (capture j) the origin is the market's FIRST sweep of
    that capture (t = its batch receipt); the pre-origin prints are the pass-j trade-sample rows copied into
    ``cb3_followup/<j+1>/pre`` (whose plan must name capture j as its previous capture) filtered to ts < t; the post-origin prints
    are the windowed fetch in ``post``. Only origins before ``origin_before`` are built. Eligibility, life fraction and fees use the
    AS-OF columns of capture j (a capture without them is ineligible, counted). Markets whose post window was not reached are
    excluded (counted); a failed or partial window makes the fill status unavailable, never 'not filled'; the pre page's own status
    and 500-print cap decide the pre-origin visibility. Marks use later first sweeps."""
    if P.asof is None:
        raise D.Cb3Error("the prospective builder needs a panel loaded with asof=True")
    rows, frows = [], []
    larges: dict[str, set[float]] = {}
    spans: dict[str, list[float]] = {}
    status_counts: dict[str, int] = {}
    diag: dict[str, int] = {"passes": 0, "passes_missing_followup": 0, "passes_misaligned": 0, "sample_markets": 0, "no_eligible_book": 0, "not_open": 0,
                            "end_too_close": 0, "no_prior_trade": 0, "kept": 0, "life_truncated": 0, "page_cap_markets": 0, "no_asof_columns": 0,
                            "post_not_reached": 0, "post_failed_unavailable": 0, "pre_fetch_failed": 0, "pre_capped": 0}
    idx = {str(x): i for i, x in enumerate(P.markets)}
    for j in range(0, P.n_caps - 1):
        if origin_before is not None and P.starts[j] >= origin_before:
            break
        diag["passes"] += 1
        nxt = P.cap_ids[j + 1]
        d = reader.root / nxt
        ok, why = _pass_aligned(d, P.cap_ids[j])
        if not ok:
            diag["passes_misaligned" if why == "misaligned" else "passes_missing_followup"] += 1
            continue
        meta = reader.meta(nxt)
        plan = json.loads((d / "plan.json").read_text())
        incl = plan.get("inclusion_float", {})
        frac = float(plan.get("frac", 0.5))
        wl = pd.read_csv(d / "pre" / "wallets.csv.gz", usecols=["market_id"], dtype=str)
        sampled = set(wl["market_id"].astype(str)) | set(incl)
        feats = _read_pre_features(d)
        diag["sample_markets"] += len(sampled)
        for mid in sorted(sampled):
            m = idx.get(mid)
            if m is None:
                continue
            t = P.mat["s1_recv"][m, j]
            bid, ask = P.mat["s1_best_bid"][m, j], P.mat["s1_best_ask"][m, j]
            if not (np.isfinite(t) and eligible_quote(float(bid), float(ask))):
                diag["no_eligible_book"] += 1
                continue
            if not P.asof_cols[j]:
                diag["no_asof_columns"] += 1
                continue
            clos, acc = P.mat["closed"][m, j], P.mat["accepting_orders"][m, j]
            end = D.epoch(P.asof["asof_end_date"][m, j]) if P.asof["asof_end_date"][m, j] else math.nan
            if clos == 1.0 or acc == 0.0:
                diag["not_open"] += 1
                continue
            if not (math.isfinite(end) and end > t + D.MAKER["end_at_margin_s"]):
                diag["end_too_close"] += 1
                continue
            if not _traded_before(P, j, m):
                diag["no_prior_trade"] += 1
                continue
            mm = meta.get("markets", {}).get(f"post:{mid}")
            pstat = (mm or {}).get("status", "not_reached")
            status_counts[pstat] = status_counts.get(pstat, 0) + 1
            if mm is None or pstat == "not_reached":
                diag["post_not_reached"] += 1
                continue
            ft = feats.get(mid)
            if ft is None or ft.get("status") != "ok":  # no recorded fetch status = unavailable pre page
                diag["pre_fetch_failed"] += 1
                continue
            pre = reader.trades(nxt, "pre", mid)
            n_ret = int(float(ft["n_returned"])) if ft and str(ft.get("n_returned", "")) not in ("", "nan") else None
            pre_cap = bool(n_ret is not None and n_ret >= VISIBLE)
            diag["pre_capped"] += int(pre_cap)
            req = mm.get("request_epoch")
            life, ltr = LIFE, False
            if req is not None and req < t + LIFE:
                life, ltr = max(float(req) - float(t), 0.0), True
                diag["life_truncated"] += 1
            partial = pstat != "ok"
            diag["post_failed_unavailable"] += int(partial)
            cap = bool(mm.get("page_cap")) or partial  # a failed / partial window: every fill status is unavailable
            diag["page_cap_markets"] += int(bool(mm.get("page_cap")))
            created = D.epoch(P.asof["asof_created_at"][m, j]) if P.asof["asof_created_at"][m, j] else math.nan
            bs, as_ = P.mat["s1_bid_size_1"][m, j], P.mat["s1_ask_size_1"][m, j]
            db, da = P.mat["s1_depth_bid_1c"][m, j], P.mat["s1_depth_ask_1c"][m, j]
            chg = P.mat["chg_1d"][m, j]
            row = P.meta.iloc[m]
            o = Opp(opp_id=f"{mid}@{int(t)}", market_id=mid, event=str(row["event_id"]), dep=str(dep_label(row)), cat=category_key(P.asof["asof_fee_category"][m, j]), t=float(t),
                    bid=float(bid), ask=float(ask), bid_size=float(bs), ask_size=float(as_), created=created, end=end,
                    abs_chg_24h=abs(float(chg)) if np.isfinite(chg) else math.nan, depth_1c_own=float(db), depth_1c_ask=float(da),
                    depth_1c_both=float(db + da) if (np.isfinite(db) and np.isfinite(da)) else math.nan,
                    fee_schedule=P.asof["asof_fee_schedule"][m, j] or None, fees_enabled=P.asof["fees_enabled"][m, j] or None,
                    truncated=cap, oldest_ts=mm.get("oldest_ts") if not partial else None, life=life, life_truncated=ltr,
                    pre_truncated=pre_cap, pre_oldest=float(pre["ts"].min()) if len(pre["ts"]) else None)
            later = np.arange(j + 1, P.n_caps)
            marks = SweepMarks(P.mat["s1_recv"][m, later], P.mat["s1_best_bid"][m, later], P.mat["s1_best_ask"][m, later]) if with_marks else None
            post = reader.trades(nxt, "post", mid)
            r, f, lg = evaluate_opportunity(o, pre, post, marks, prospective=True, cuts=cuts)
            w = 1.0 / (float(incl.get(mid) or 1.0) * frac)
            r.update(w=w, closed_early=False, cap_id=P.cap_ids[j])
            for x in f:
                x.update(w=w, closed_early=False, cap_id=P.cap_ids[j])
                x["net_wc"] = x["net6"] if math.isfinite(x["net6"]) else x["wc_mo"]  # unavailable mark: the worst-case mark-out, no rebate
            larges.setdefault(mid, set()).update(lg)
            tsall = np.r_[pre["ts"], post["ts"]]
            if len(tsall):
                sp = spans.setdefault(mid, [float(tsall.min()), float(tsall.max())])
                sp[0], sp[1] = min(sp[0], float(tsall.min())), max(sp[1], float(tsall.max()))
            rows.append(r)
            frows.extend(f)
            diag["kept"] += 1
    diag["post_status_counts"] = status_counts  # type: ignore[assignment]
    return {"opps": pd.DataFrame(rows), "fills": pd.DataFrame(frows), "diag": diag,
            "large_times": {k: np.array(sorted(v)) for k, v in larges.items()}, "spans": {k: (v[0], v[1]) for k, v in spans.items()}}


def _read_pre_features(d: Path) -> dict[str, dict]:
    """Per-market status of the trade-sample fetch (copied unchanged into ``pre/features.csv.gz`` by the follow-up step)."""
    p = d / "pre" / "features.csv.gz"
    if not p.exists():
        return {}
    df = pd.read_csv(p, dtype=str, keep_default_na=False)
    return {r["market_id"]: r for r in df.to_dict("records")}


def dep_label(row) -> str:
    nr = str(row.get("neg_risk_id", "") or "")
    par = str(row.get("parent_event_ids", "") or "").strip("[]\"' ").split(",")[0].strip("\"' ")
    return f"nr:{nr}" if nr else (f"pe:{par}" if par else f"ev:{row.get('event_id', '')}")


def screen_prospective(P, reader: FollowupReader, cuts: dict, tests: list[str], *, stage: int, origin_before: float,
                       n_boot: int = D.N_BOOT, placebo_draws: int = D.PLACEBO_DRAWS, random_draws: int = D.RANDOM_FILTER_DRAWS) -> dict:
    """Stage 2 (``stage=2``) / Stage P (``stage=3``, the economic tests only) of the B tests in ``tests`` on the follow-up sample at recorded
    books and prints. UTC-day way with the CB2 small-G rule. B1's circular-shift placebo uses the real large-order streams the builder keeps; B3/B5 permute within market."""
    u = build_prospective(P, reader, origin_before=origin_before, cuts=cuts)
    opps, fills = u["opps"], u["fills"]
    out: dict = {"stage": stage, "exclusions": u["diag"], "tests": {}, "placebo": {}, "descriptive": {}}
    if not len(opps):
        out["note"] = "no quote opportunities"
        return out
    o_ns, f_ns, o_sp, f_sp = scope_split(opps, fills)
    out["descriptive"]["U_non_sports"] = u_baseline(o_ns, f_ns)
    out["descriptive"]["U_sports_stratum"] = u_baseline(o_sp, f_sp) if len(o_sp) else {"n_quotes": 0}
    out["descriptive"]["capacity"] = capacity(f_ns[f_ns["rule"] == "queue"], o_ns)
    ways, sg = ["event", "dep", "day"], ("day",)
    alpha_stage = 2
    q = attach_fill_features(f_ns[f_ns["rule"] == "queue"], o_ns)
    qm = q[np.isfinite(q["net6"])].copy()
    large_times, spans = u["large_times"], u["spans"]  # the real large-order streams of the follow-up data (freeze-check fix 12)
    for tid in tests:
        if tid == "B1":
            out["tests"][tid] = mech_stage(qm[qm["classifiable"].astype(bool)], "B1", "post", ways=ways, small_g=sg, stage=alpha_stage, history=False, n_boot=n_boot, draws=placebo_draws,
                                           placebo_fn=lambda d, s: placebo_circular_shift(d, large_times, spans, s))
        elif tid == "B3":
            out["tests"][tid] = mech_stage(qm[qm["lf"].notna()], "B3", "lf", ways=ways, small_g=sg, stage=alpha_stage, history=False, n_boot=n_boot, draws=placebo_draws,
                                           placebo_fn=lambda d, s: placebo_permute_within_market(d, "lf", s), week_fe=True)
        elif tid == "B5":
            b5 = opp_level_frame(o_ns, f_ns)
            out["tests"][tid] = mech_stage(b5, "B5", "rt", ways=ways, small_g=sg, stage=alpha_stage, history=False, n_boot=n_boot, draws=placebo_draws, b5=True,
                                           placebo_fn=lambda d, s: placebo_permute_within_market(d, "rt", s), order="t_fill", target="ev_quote")
        elif tid in ("B2", "B4", "B6"):
            out["tests"][tid] = econ_test(o_ns, f_ns, tid, cuts=cuts, stage=2, weights="w", draws=random_draws, n_boot=n_boot, small_g=sg, ways=ways)
        else:
            raise ValueError(tid)
        if "placebo" in out["tests"][tid]:
            out["placebo"][tid] = out["tests"][tid]["placebo"]
    if stage == 3:
        out["tests"] = {k: v for k, v in out["tests"].items() if k in D.STAGEP_TESTS}
    return out


def stage2_mde(counts: dict) -> dict:
    """Stage-2 MDE (80% power, one-sided 5%: 2.8 x SE) from census COUNTS. The outcome SDs are the design's stated assumptions (net per
    fill SD 6c; SD of LF 0.28; SD of RT 0.15; share of post-large fills 0.15), NOT estimated from any outcome: q0064 computes no
    outcome. Overlapping 6h marks of one market and the day way enter through a repeated-market design effect estimated from the
    row counts per market (1 + (mean rows per market - 1) x 0.25, an assumed within-market correlation) and a 5% small-G inflation."""
    n_f, n_m = counts.get("fills_queue", 0), max(counts.get("fill_markets", 1), 1)
    n_o = counts.get("rt_defined_opportunities", 0)
    if n_f < 2:
        return {"note": "too few fills"}
    deff = 1.0 + (n_f / n_m - 1.0) * 0.25
    infl = 1.05
    sd = 0.06
    se_mean = sd * math.sqrt(deff / n_f) * infl
    out = {"assumptions": {"sd_net_per_fill": sd, "sd_lf": 0.28, "sd_rt": 0.15, "p_post": 0.15, "rho_within_market": 0.25, "small_g_inflation": infl},
           "design_effect": deff, "B2_B4_mde": 2.8 * se_mean, "B6_mde": 2.8 * sd * math.sqrt(deff / max(n_f * 0.1, 1.0)) * infl,
           "B1_mde_slope": 2.8 * se_mean / math.sqrt(0.15 * 0.85),
           "B3_mde_per_unit_lf": 2.8 * se_mean / 0.28}
    out["B5_mde_per_unit_rt"] = 2.8 * (sd / 2.0) * math.sqrt(deff / max(n_o, 1)) * infl / 0.15
    return out


def census_prospective(P, reader: FollowupReader, *, followup_root: Path, qs_root: Path, origin_before: float | None = None) -> dict:
    """q0064: counts only for the prospective dev window (the caller loads ``P`` from ``max(T3_fu_start, T_J4R_end)``). Follow-up
    coverage, opportunities and fills per pass (no marks built), vacuum-stratum sizes, bytes per pass, created_at coverage, page-cap hits
    and the Stage-2 MDEs from counts."""
    u = build_prospective(P, reader, with_marks=False, origin_before=origin_before)
    opps, fills = u["opps"], u["fills"]
    if len(opps):
        opps = opps.drop(columns=[c for c in opps.columns if c.endswith("_wc_mo")])
    if len(fills):
        fills = fills.drop(columns=[c for c in MARK_COLS + ("net_wc",) if c in fills.columns])
    assert_no_marks(opps)
    assert_no_marks(fills)
    metas = [reader.meta(c) for c in P.cap_ids]
    reqs = sum(m.get("requests", 0) for m in metas)
    n429 = sum(m.get("n_429", 0) for m in metas)
    vac = []
    for c in P.cap_ids:
        pth = Path(followup_root) / c / "vacuum_plan.json"
        if pth.exists():
            vp = json.loads(pth.read_text())
            vac.append({"n_onsets": vp.get("n_onsets", 0), "n_drawn": vp.get("n_drawn", 0)})
    def _bytes(p: Path) -> int:
        return sum(f.stat().st_size for f in Path(p).rglob("*") if f.is_file()) if Path(p).exists() else 0
    out = {"n_passes_window": P.n_caps, "followup_requests": int(reqs), "followup_429": int(n429),
           "passes_missing_followup": u["diag"]["passes_missing_followup"], "passes_misaligned": u["diag"]["passes_misaligned"],
           "post_status_counts": u["diag"]["post_status_counts"], "page_cap_markets": u["diag"]["page_cap_markets"],
           "life_truncated_quotes": u["diag"]["life_truncated"], "exclusions": u["diag"], "n_quote_opportunities": int(len(opps)),
           "vacuum_stratum": {"passes_with_plan": len(vac), "n_onsets_total": int(sum(v["n_onsets"] for v in vac)), "n_drawn_total": int(sum(v["n_drawn"] for v in vac))},
           "followup_bytes": {c: _bytes(Path(followup_root) / c) for c in P.cap_ids}, "quote_state_bytes": _bytes(Path(qs_root) / "quote_state"),
           "created_at_coverage": float((P.asof["asof_created_at"][P.present] != "").mean()) if P.present.any() else None,
           "captures_without_asof_columns": int((~P.asof_cols).sum())}
    if len(opps):
        o_ns, f_ns, o_sp, _f = scope_split(opps, fills)
        q = f_ns[f_ns["rule"] == "queue"] if len(f_ns) else f_ns
        out["n_quote_opportunities_non_sports"] = int(len(o_ns))
        out["fills_by_rule_side"] = {f"{r}_{s}": int(((fills["rule"] == r) & (fills["side"] == s)).sum()) for r in RULES for s in SIDES}
        out["unavailable_quotes"] = {f"{r}_{s}": int((opps[f"{r}_{s}_status"] == -1).sum()) for r in RULES for s in SIDES}
        out["rt_defined_opportunities"] = int(o_ns["rt"].notna().sum())
        out["lf_defined_opportunities"] = int(o_ns["lf_t"].notna().sum())
        out["classifiable_share"] = float(o_ns["classifiable"].mean()) if len(o_ns) else None
        out["clusters"] = {"event": int(o_ns["event"].nunique()), "dep": int(o_ns["dep"].nunique()), "day": int(o_ns["day"].nunique())}
        out["rows_per_market"] = {"opportunities": float(o_ns.groupby("market_id").size().mean()) if len(o_ns) else None}
        out["stage2_mde"] = stage2_mde({"fills_queue": int(len(q)), "fill_markets": int(q["market_id"].nunique()) if len(q) else 1,
                                        "rt_defined_opportunities": out["rt_defined_opportunities"]})
    return out
