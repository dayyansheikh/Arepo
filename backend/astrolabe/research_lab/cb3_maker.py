# ruff: noqa: E501
"""CB3 family B and the shared paper maker (docs/research_lab/CREATIVE_BATCH_3.md §2.1, §2.6, §3 CB3-B, §4.1).

Selective maker (CH39 post-print retreat, CH40 late-life schedule, CH41-narrow round-trip share) against the unfiltered
maker U. Prices and mark-outs are in price units (1c = 0.01). Paper rules only; no trading, no rewards in any primary.

Pure functions over arrays/DataFrames; the history loader reads the pmxt book table and h2 trades through the CB1 history
helpers (imported, not copied), the prospective loader reads ``quote_state/`` and ``cb3_followup/`` through
:class:`FollowupReader`. Family A re-uses the maker (fills, rebate, marks) from here for A3.
"""

from __future__ import annotations

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


def fee_rate(cat, fee_schedule=None, *, prospective: bool = False) -> float:
    """History: the docs table by category. Prospective: sidecar ``fee_schedule``, policy 'conservative'."""
    key = category_key(cat)
    if prospective:
        spec = economics.fee_spec(fee_schedule, None, key or None)
        r = economics.resolve_rate(spec, D.MAKER["rebate_fee_policy_prospective"])
        return float(r) if math.isfinite(r) else float(economics.MAX_DOCS_RATE)
    return float(economics.DOCS_CATEGORY_RATE.get(key, economics.MAX_DOCS_RATE))


def rebate_per_share(price: float, cat, *, fee_schedule=None, prospective: bool = False, halved: bool = False) -> float:
    """``rho_cat * r_cat * P (1 - P)`` per filled share (maker fee 0). Unknown/null category: rho = 0."""
    rho = rebate_share(cat)
    if rho == 0.0:
        return 0.0
    out = rho * fee_rate(cat, fee_schedule, prospective=prospective) * float(price) * (1.0 - float(price))
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


def prints_union(pre: dict[str, np.ndarray], post: dict[str, np.ndarray], t: float) -> dict[str, np.ndarray]:
    """pre/ filtered to ``ts < t``, post/ to ``ts > t``, de-duplicated (a print in both counts once), time-sorted (item 5).
    Dedup key: ``trade_key`` / tx hash if stored, else the (side, outcome, price, size, ts) tuple."""
    a = _take(pre, pre["ts"] < t) if len(pre["ts"]) else pre
    b = _take(post, post["ts"] > t) if len(post["ts"]) else post
    cat = {k: np.concatenate([a[k], b[k]]) for k in a}
    if not len(cat["ts"]):
        return cat
    key = np.array([f"{k}|{s}|{o}|{p:.8f}|{z:.8f}|{ts:.3f}" for k, s, o, p, z, ts in
                    zip(cat["key"], cat["side_raw"], cat["outcome"], cat["p0"], cat["size"], cat["ts"], strict=True)], object)
    _u, first = np.unique(key, return_index=True)
    keep = np.zeros(len(key), bool)
    keep[first] = True
    out = _take(cat, keep)
    o = np.argsort(out["ts"], kind="stable")
    return {k: v[o] for k, v in out.items()}


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
        if i < 0:
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
        return np.isfinite(self.bid) & np.isfinite(self.ask) & (self.bid < self.ask) & (self.ask < 1) & ((self.ask - self.bid) <= D.MAKER["spread_max"] + 1e-12)

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
    depth_1c_own: float = math.nan
    depth_1c_both: float = math.nan
    fee_schedule: object = None
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
    rt = round_trip_share(vis, t, truncated=o.truncated, oldest_ts=o.oldest_ts)
    spread = o.ask - o.bid
    mid = (o.ask + o.bid) / 2.0
    lf_t = life_fraction(t, o.created, o.end)
    row = {
        "opp_id": o.opp_id, "market_id": o.market_id, "event": o.event, "dep": o.dep, "cat": category_key(o.cat), "t": t,
        "week": c1.iso_week(t), "day": pd.Timestamp(t, unit="s", tz="UTC").strftime("%Y-%m-%d"),
        "bid": o.bid, "ask": o.ask, "spread": spread, "mid": mid, "bid_size": o.bid_size, "ask_size": o.ask_size,
        "lf_t": lf_t, "classifiable": bool(classifiable), "t_cancel": t_cancel, "cancel_offset": t_cancel - t if math.isfinite(t_cancel) else math.nan,
        "activity": activity, "rt": rt, "abs_chg_24h": o.abs_chg_24h, "depth_own_bid": o.depth_1c_own, "depth_both": o.depth_1c_both,
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
    reb = rebate_per_share(price, o.cat, fee_schedule=o.fee_schedule, prospective=prospective)
    reb_h = rebate_per_share(price, o.cat, fee_schedule=o.fee_schedule, prospective=prospective, halved=True)
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


def history_market_units(rec: dict, books_m: pd.DataFrame, ts_p: np.ndarray, vals_p: np.ndarray, tr: pd.DataFrame | None,
                         truncated: bool, oldest_ts, ctx: c1.Ctx, cuts: dict | None, dep: str | None = None,
                         chg: dict[float, float] | None = None) -> tuple[list[dict], list[dict], set[float], tuple[float, float] | None, dict]:
    """Quote opportunities, fills and large-order times of one history market at its pmxt 6h-grid books (both book clocks <= t).
    Population: binary, open, traded before t (unavailable if unknown: leaves the population, counted), end_at > t + 8h,
    eligible book, category in scope (sports reported as a stratum by the caller). Returns (opp rows, fill rows, large times,
    (first, last) print ts, diag)."""
    pr = prints_arrays(tr)
    diag = {"origins": 0, "not_eligible_book": 0, "not_open": 0, "end_too_close": 0, "trade_state_unavailable": 0, "no_prior_trade": 0, "kept": 0}
    rows, frows, larges = [], [], set()
    marks = HistoryMarks(ts_p, vals_p)
    cat = category_key(rec.get("fee_category"))
    old = c1.oldest_or_inf(oldest_ts) if truncated else None
    for b in books_m.itertuples():
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
        o = Opp(opp_id=f"{rec['market_id']}@{int(t)}", market_id=rec["market_id"], event=rec["event_id"], dep=dep or rec["event_id"], cat=cat, t=t,
                bid=bid, ask=ask, bid_size=float(getattr(b, "sw_bid_size_1", math.nan)), ask_size=float(getattr(b, "sw_ask_size_1", math.nan)),
                created=rec["created_epoch"], end=rec["end_epoch"], abs_chg_24h=abs(chg.get(t, math.nan)) if chg else math.nan,
                depth_1c_own=float(getattr(b, "sw_bid_size_1", math.nan)), depth_1c_both=float(getattr(b, "sw_bid_size_1", 0) or 0) + float(getattr(b, "sw_ask_size_1", 0) or 0),
                truncated=truncated, oldest_ts=old)
        row, fl, lg = evaluate_opportunity(o, pr, pr, marks, prospective=False, cuts=cuts)
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
    f = fills.join(o[["spread", "mid", "abs_chg_24h", "price_band", "spread_band", "depth_both", "taker_notional_24h", "bid_size", "ask_size", "classifiable", "lf_t", "rt", "t_cancel"]], on="opp_id")
    f["depth_own"] = np.where(f["side"] == "bid", f["bid_size"], f["ask_size"])
    return f


def opp_level_frame(opps: pd.DataFrame, fills: pd.DataFrame, rule: str = "queue") -> pd.DataFrame:
    """B5 frame: one row per quote opportunity with RT defined; ``ev_quote`` = sum of marked net over its fills / 2 (0 if none)."""
    f = fills[(fills["rule"] == rule) & np.isfinite(fills["net6"])].groupby("opp_id")["net6"].sum()
    o = opps[opps["rt"].notna()].copy()
    o["ev_quote"] = o["opp_id"].map(f).fillna(0.0) / 2.0
    o["depth_own"] = o["bid_size"]
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
        import json

        p = self.root / pass_id / "meta.json"
        return json.loads(p.read_text()) if p.exists() else {}

    def trades(self, pass_id: str, part: str, market_id: str) -> dict[str, np.ndarray]:
        p = self.root / pass_id / part / "trades.csv.gz"
        if not p.exists():
            return prints_arrays(None)
        df = pd.read_csv(p, dtype={"market_id": str, "wallet_hash": str, "trade_key": str})
        return prints_arrays(df[df["market_id"].astype(str) == str(market_id)])
