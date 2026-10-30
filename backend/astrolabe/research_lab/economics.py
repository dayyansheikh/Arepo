"""Paper-only execution-cost model for research evaluation (design H2a/H2b, Phase 8 prerequisite).

AREPO never trades. Nothing here places, signs or simulates an order against a live venue; it
prices hypothetical fills against already-recorded public book sweeps. Results are "optimistic,
not tradable": no latency, queue position or market impact beyond the recorded depth.

Sources
-------
* Fee formula: Polymarket docs https://docs.polymarket.com/trading/fees (retrieved 2026-10-11):
  ``fee = C * feeRate * p * (1 - p)``, takers only, USDC, rounded to 5 decimals. The per-market
  ``feeSchedule`` of the Gamma API (``{"exponent":1,"rate":r,"rebateRate":..,"takerOnly":true}``)
  generalises this to ``C * rate * (p*(1-p))**exponent``; every observed schedule has exponent 1.
  ``takerBaseFee`` (observed 1000) is NOT a rate for this formula and is ignored.
* Book format: ``book_sweep.py`` rows give top-of-book and cumulative depth within 1c and 5c only.
  A fill walked on that summary is therefore an upper bound on cost (each depth band is priced at
  its outer edge). Full ``levels`` may be passed instead for an exact walk.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import compare, evaluate

FEE_DOCS_URL = "https://docs.polymarket.com/trading/fees"
FEE_DOCS_RETRIEVED = "2026-10-11"
FEE_TABLE_VERSION = "fee-table-v1"
FEE_DECIMALS = 5

# Docs rate per ``fee_category`` (research_panel.pairing.fee_category keys). Cross-check and
# conservative fallback only; the per-market feeSchedule is the primary source.
DOCS_CATEGORY_RATE: dict[str, float] = {
    "crypto": 0.07,
    "sports": 0.05, "economics": 0.05, "culture": 0.05, "weather": 0.05, "other": 0.05,
    "finance": 0.04, "politics": 0.04, "mentions": 0.04, "tech": 0.04,
    "geopolitics": 0.0,
}
MAX_DOCS_RATE = max(DOCS_CATEGORY_RATE.values())

# Maker rebate share of taker fees by category (docs.polymarket.com/trading/fees, fetched
# 2026-10-12). Moved here from scripts/econ_conditions_maker.py (which imports it); a category
# absent from the table (or unknown) has share 0.
REBATE_SHARE: dict[str, float] = {
    "crypto": 0.20, "sports": 0.15, "finance": 0.25, "politics": 0.25, "economics": 0.25,
    "culture": 0.25, "weather": 0.25, "other": 0.25, "mentions": 0.25, "tech": 0.25,
    "geopolitics": 0.0,
}


# --- 1. fee table -----------------------------------------------------------------------------


@dataclass(frozen=True)
class FeeSpec:
    """Per-market taker fee. ``rate`` is NaN when unknown; ``flag`` says why."""

    rate: float
    exponent: float = 1.0
    flag: str = "ok"  # ok | disabled | unknown_schedule | unknown_fees_enabled
    docs_rate: float = math.nan
    cross_check: str = "no_docs_rate"  # match | schedule_below_docs | schedule_above_docs | ...

    @property
    def known(self) -> bool:
        return not math.isnan(self.rate)


def _docs_rate(fee_category: str | None) -> float:
    if not fee_category:
        return math.nan
    key = str(fee_category).split(":")[0]
    return DOCS_CATEGORY_RATE.get(key, math.nan)


def parse_fee_schedule(raw) -> tuple[float, float] | None:
    """``(rate, exponent)`` from a feeSchedule JSON string/dict; None if unusable."""
    if raw is None or (isinstance(raw, float) and math.isnan(raw)):
        return None
    try:
        d = json.loads(raw) if isinstance(raw, str) else raw
        rate = float(d["rate"])
        exp = float(d.get("exponent", 1))
    except (TypeError, ValueError, KeyError, json.JSONDecodeError):
        return None
    if not (math.isfinite(rate) and math.isfinite(exp)) or rate < 0 or exp <= 0:
        return None
    return rate, exp


def fee_spec(fee_schedule=None, fees_enabled=None, fee_category: str | None = None) -> FeeSpec:
    """Taker fee spec for one market from sidecar fields.

    fees disabled -> rate 0 (flag ``disabled``). Enabled but schedule absent/unparseable, or the
    enabled flag itself missing with no schedule -> rate NaN with a flag, never 0.
    """
    docs = _docs_rate(fee_category)
    enabled = None
    if fees_enabled is not None and not pd.isna(fees_enabled):
        enabled = bool(int(float(fees_enabled)))
    if enabled is False:
        return FeeSpec(0.0, 1.0, "disabled", docs, "disabled")
    sched = parse_fee_schedule(fee_schedule)
    if sched is None:
        flag = "unknown_fees_enabled" if enabled is None else "unknown_schedule"
        return FeeSpec(math.nan, 1.0, flag, docs, "no_schedule")
    rate, exp = sched
    if math.isnan(docs):
        cc = "no_docs_rate"
    elif abs(rate - docs) < 1e-12:
        cc = "match"
    else:
        cc = "schedule_below_docs" if rate < docs else "schedule_above_docs"
    return FeeSpec(rate, exp, "ok", docs, cc)


def resolve_rate(spec: FeeSpec, policy: str = "max_if_unknown") -> float:
    """Rate used in P&L. ``schedule``: the schedule rate (NaN stays NaN). ``max_if_unknown``
    (design default): unknown -> highest rate in the table. ``conservative``: max(schedule,
    docs)."""
    if policy not in ("schedule", "max_if_unknown", "conservative"):
        raise ValueError(policy)
    if not spec.known:
        return math.nan if policy == "schedule" else MAX_DOCS_RATE
    if policy == "conservative" and not math.isnan(spec.docs_rate):
        return max(spec.rate, spec.docs_rate)
    return spec.rate


def taker_fee(shares: float, price: float, rate: float, exponent: float = 1.0) -> float:
    """USDC taker fee ``C*rate*(p(1-p))**exp`` rounded to 5 dp. NaN rate -> NaN."""
    if math.isnan(rate) or math.isnan(price) or shares <= 0:
        return math.nan if math.isnan(rate) else 0.0
    p = min(max(price, 0.0), 1.0)
    return round(shares * rate * (p * (1.0 - p)) ** exponent, FEE_DECIMALS)


# --- 2. execution from a book sweep -----------------------------------------------------------


def _tick_round(price: float, tick: float | None, up: bool) -> float:
    if not tick or tick <= 0:
        return price
    n = price / tick
    n = math.ceil(n - 1e-9) if up else math.floor(n + 1e-9)
    return round(n * tick, 10)


def side_levels(book: dict, side: str) -> list[tuple[float, float]]:
    """Levels the taker consumes, best first, as (price, size) in the TRADED token's terms.

    ``side``: ``buy0`` (lift token-0 asks), ``sell0`` (hit token-0 bids), ``buy1`` (token-1 bought
    against token-0 bids: price 1-bid) and ``sell1`` (token-1 sold into token-0 asks: 1-ask).
    ``book['levels_bids'|'levels_asks']`` (lists of (price,size)) give an exact walk; otherwise the
    sweep summary is expanded conservatively (1c band at best+/-1c, 5c band at best+/-5c).
    """
    if side not in ("buy0", "sell0", "buy1", "sell1"):
        raise ValueError(side)
    lift_asks = side in ("buy0", "sell1")  # consumes the token-0 ask side
    key = "ask" if lift_asks else "bid"
    exact = book.get("levels_asks" if lift_asks else "levels_bids")
    tick = book.get("tick_size")
    tick = None if tick is None or pd.isna(tick) else float(tick)
    if exact is not None:
        lv = sorted(((float(p), float(s)) for p, s in exact if s > 0), reverse=not lift_asks)
    else:
        best, s1 = book.get(f"best_{key}"), book.get(f"{key}_size_1")
        if best is None or s1 is None or pd.isna(best) or pd.isna(s1) or s1 <= 0:
            return []
        d1, d5 = book.get(f"depth_{key}_1c"), book.get(f"depth_{key}_5c")
        d1 = s1 if d1 is None or pd.isna(d1) else max(float(d1), float(s1))
        d5 = d1 if d5 is None or pd.isna(d5) else max(float(d5), d1)
        sgn = 1.0 if lift_asks else -1.0
        lv = [(float(best), float(s1))]
        for extra, width in ((d1 - s1, 0.01), (d5 - d1, 0.05)):
            if extra > 1e-12:
                # pessimistic for the taker: lift asks round UP, hit bids round DOWN
                lv.append((_tick_round(float(best) + sgn * width, tick, up=lift_asks), extra))
    if side in ("buy1", "sell1"):
        lv = [(round(1.0 - p, 10), s) for p, s in lv]
    return lv


@dataclass
class Fill:
    side: str
    shares: float
    filled: float
    vwap: float  # NaN when nothing filled
    best: float  # touch price on the traded side (NaN if book side empty)
    mid: float  # token-terms mid of the touch (NaN if one-sided)
    cash: float  # USDC paid (buy) / received (sell) for the filled shares, before fee
    half_spread_cost: float  # USDC, shares*|best-mid| ; NaN if no mid
    impact_cost: float  # USDC, filled*|vwap-best|
    fee: float  # USDC (NaN if rate unknown)
    depth_exhausted: bool
    flags: list[str] = field(default_factory=list)

    @property
    def total_cost(self) -> float:
        return self.half_spread_cost + self.impact_cost + self.fee


def min_size(book: dict) -> float:
    ms = book.get("min_order_size")
    ms = 0.0 if ms is None or pd.isna(ms) else float(ms)
    return max(1.0, ms)


def sweep_fill(book: dict, side: str, shares: float | None = None, rate: float = math.nan,
               exponent: float = 1.0) -> Fill:
    """Walk the book for ``shares`` (default ``max(1, orderMinSize)``)."""
    q = min_size(book) if shares is None else float(shares)
    flags: list[str] = []
    if q < min_size(book) - 1e-12:
        flags.append("below_order_min_size")
    lv = side_levels(book, side)
    if not lv:
        return Fill(side, q, 0.0, math.nan, math.nan, math.nan, 0.0, math.nan, math.nan,
                    math.nan if math.isnan(rate) else 0.0, True, [*flags, "empty_side"])
    need, cash, got = q, 0.0, 0.0
    for p, s in lv:
        take = min(need, s)
        cash += take * p
        got += take
        need -= take
        if need <= 1e-12:
            break
    exhausted = need > 1e-12
    if exhausted:
        flags.append("depth_exhausted")
    vwap = cash / got
    best = lv[0][0]
    # token-terms mid of the recorded touch: needs both sides of the book
    bb, ba = book.get("best_bid"), book.get("best_ask")
    if bb is None or ba is None or pd.isna(bb) or pd.isna(ba):
        mid = math.nan
        flags.append("one_sided_no_mid")
    else:
        mid0 = (float(bb) + float(ba)) / 2.0
        mid = mid0 if side.endswith("0") else 1.0 - mid0
    hs = got * abs(best - mid) if not math.isnan(mid) else math.nan
    impact = got * abs(vwap - best)
    fee = taker_fee(got, vwap, rate, exponent)
    if math.isnan(rate):
        flags.append("fee_unknown")
    return Fill(side, q, got, vwap, best, mid, cash, hs, impact, fee, exhausted, flags)


# --- 3. paper P&L -----------------------------------------------------------------------------

_BOOK_FIELDS = ["best_bid", "best_ask", "bid_size_1", "ask_size_1", "depth_bid_1c", "depth_ask_1c",
                "depth_bid_5c", "depth_ask_5c", "tick_size", "min_order_size"]


def _book(row, prefix: str) -> dict:
    return {f: row.get(prefix + f) for f in _BOOK_FIELDS}


def signal(p_up: float, p_down: float, tau: float) -> int:
    """+1 buy outcome 0, -1 buy outcome 1, 0 no trade (design: P(up)-P(down) vs +-tau)."""
    d = p_up - p_down
    return 1 if d > tau else -1 if d < -tau else 0


def paper_trade(row: dict, tau: float, exit_mode: str = "sweep", fee_policy: str = "max_if_unknown",
                p_up_col: str = "p_up", p_down_col: str = "p_down") -> dict:
    """One origin -> per-trade record. ``row`` carries ``en_*`` (entry sweep) and ``ex_*`` (exit
    sweep) book fields, ``gx_best_bid``/``gx_best_ask`` (Gamma target snapshot, sensitivity exit),
    ``fee_schedule``/``fees_enabled``/``fee_category`` and the model probabilities.

    status: no_signal | no_entry_book | entry_top_size | entry_depth | no_exit | traded.
    Unfilled exit shares are valued at 0 (conservative) and flagged ``exit_depth_exhausted``.
    """
    out = {"traded": False, "status": "no_signal", "direction": 0, "pnl": 0.0}
    d = signal(float(row[p_up_col]), float(row[p_down_col]), tau)
    out["direction"] = d
    if d == 0:
        return out
    spec = fee_spec(row.get("fee_schedule"), row.get("fees_enabled"), row.get("fee_category"))
    rate = resolve_rate(spec, fee_policy)
    out["fee_flag"] = spec.flag
    buy_side, sell_side = ("buy0", "sell0") if d > 0 else ("buy1", "sell1")
    en = _book(row, "en_")
    q = min_size(en)
    lv = side_levels(en, buy_side)
    if not lv:
        out["status"] = "no_entry_book"
        return out
    if lv[0][1] < q:
        out["status"] = "entry_top_size"
        return out
    buy = sweep_fill(en, buy_side, q, rate, spec.exponent)
    if buy.depth_exhausted:
        out["status"] = "entry_depth"
        return out
    if exit_mode == "sweep":
        ex = _book(row, "ex_")
        if all(ex[f] is None or pd.isna(ex[f]) for f in ("best_bid", "best_ask")):
            out["status"] = "no_exit"
            return out
        sell = sweep_fill(ex, sell_side, q, rate, spec.exponent)
        recv, sfee, sflags = sell.cash, sell.fee, sell.flags
        hs_x, imp_x = sell.half_spread_cost, sell.impact_cost
        sold = sell.filled
    elif exit_mode == "gamma_bid":
        gb, ga = row.get("gx_best_bid"), row.get("gx_best_ask")
        px = gb if d > 0 else (None if ga is None or pd.isna(ga) else 1.0 - float(ga))
        if px is None or pd.isna(px):
            out["status"] = "no_exit"
            return out
        recv, sold, sflags = q * float(px), q, []
        sfee = taker_fee(q, float(px), rate, spec.exponent)
        hs_x = imp_x = 0.0
    else:
        raise ValueError(exit_mode)
    pnl = recv - buy.cash - buy.fee - sfee
    out.update(traded=True, status="traded", shares=q, entry_vwap=buy.vwap, entry_cash=buy.cash,
               exit_cash=recv, fee_entry=buy.fee, fee_exit=sfee,
               half_spread_entry=buy.half_spread_cost, impact_entry=buy.impact_cost,
               half_spread_exit=hs_x, impact_exit=imp_x, pnl=pnl,
               exit_depth_exhausted=bool(sold < q - 1e-12), exit_flags=sflags)
    return out


def paper_pnl(df: pd.DataFrame, tau: float, **kw) -> pd.DataFrame:
    """Vector wrapper: one record per row of ``df`` (index preserved)."""
    recs = [paper_trade(r, tau, **kw) for r in df.to_dict("records")]
    return pd.DataFrame(recs, index=df.index)


# --- clustered, one-sided economic tests ------------------------------------------------------

MIN_TRADES = 30
MIN_CLUSTERS = 10


def _cluster_sums(cluster: np.ndarray, num: np.ndarray, den: np.ndarray):
    codes, uniq = pd.factorize(cluster)
    k = len(uniq)
    return (np.bincount(codes, weights=num, minlength=k),
            np.bincount(codes, weights=den, minlength=k), k)


def boot_ratio(cluster: np.ndarray, num: np.ndarray, den: np.ndarray,
               n_boot: int = evaluate.BOOT_N, seed: int = evaluate.BOOT_SEED) -> dict:
    """Ratio-of-cluster-sums bootstrap with the SAME draw scheme as ``compare.paired_bootstrap``
    (default_rng(seed), ``integers(0,k,k)`` per resample), so draws are shared with H1 whenever the
    cluster array is the same. One-sided lower bound = 5th percentile. The two-sided 95% CI is
    taken from ``compare.paired_bootstrap`` itself (mean = R2 - 1 with weights den, -num)."""
    cn, cd, k = _cluster_sums(cluster, num, den)
    rng = np.random.default_rng(seed)
    m = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.integers(0, k, size=k)
        d = cd[idx].sum()
        m[i] = cn[idx].sum() / d if d > 0 else np.nan
    pb = compare.paired_bootstrap(cluster, {"den": den.astype(float), "neg": -num.astype(float)},
                                  "den", n_boot, seed)
    lo, hi = pb["models"]["neg"]  # R2 = 1 - (-num)/den = 1 + mean
    return {"mean": float(num.sum() / den.sum()) if den.sum() > 0 else math.nan,
            "lower_5pct": float(np.nanpercentile(m, 5)),
            "ci95_two_sided": [lo - 1.0, hi - 1.0], "n_clusters": int(k)}


def h2a(trades: pd.DataFrame, clusters: dict[str, np.ndarray], **kw) -> dict:
    """H2a: net mean P&L per trade > 0. ``trades`` = paper_pnl output over ALL H2-qualifying
    origins (non-traded rows contribute nothing); ``clusters`` maps definition name -> array
    aligned with ``trades``. Rejects only if the one-sided lower bound > 0 under EVERY definition;
    <30 trades or <10 clusters with a trade -> not testable (never rejected)."""
    t = trades["traded"].to_numpy(bool)
    pnl = np.where(t, trades["pnl"].to_numpy(float), 0.0)
    n = int(t.sum())
    res: dict = {"hypothesis": "H2a", "n_trades": n, "per_definition": {}}
    ok_clusters = True
    for name, c in clusters.items():
        c = np.asarray(c)
        nc = int(pd.Series(c[t]).nunique())
        r = boot_ratio(c, pnl, t.astype(float), **kw) if n else {"mean": math.nan,
                                                                  "lower_5pct": math.nan}
        r["clusters_with_trade"] = nc
        ok_clusters &= nc >= MIN_CLUSTERS
        res["per_definition"][name] = r
    res["testable"] = bool(n >= MIN_TRADES and ok_clusters)
    res["reject"] = bool(res["testable"] and all(
        r["mean"] > 0 and r["lower_5pct"] > 0 for r in res["per_definition"].values()))
    return res


def h2b(f_trades: pd.DataFrame, m0_trades: pd.DataFrame, clusters: dict[str, np.ndarray],
        **kw) -> dict:
    """H2b: mean over all qualifying origins of (P&L_F - P&L_M0), no-trade = 0, > 0, one-sided,
    same clusters and rejection-under-every-definition rule. Both frames share an index/origins."""
    if not f_trades.index.equals(m0_trades.index):
        raise ValueError("F* and M0 trade frames must cover the same origins in the same order")
    diff = (np.where(f_trades["traded"], f_trades["pnl"], 0.0)
            - np.where(m0_trades["traded"], m0_trades["pnl"], 0.0)).astype(float)
    ones = np.ones(len(diff))
    res: dict = {"hypothesis": "H2b", "n_origins": len(diff), "per_definition": {}}
    for name, c in clusters.items():
        res["per_definition"][name] = boot_ratio(np.asarray(c), diff, ones, **kw)
    res["reject"] = bool(all(r["mean"] > 0 and r["lower_5pct"] > 0
                             for r in res["per_definition"].values()))
    return res


# --- 4. break-even analysis -------------------------------------------------------------------

PRICE_BANDS = [0.0, 0.05, 0.20, 0.80, 0.95, 1.0000001]
PRICE_LABELS = ["<0.05", "0.05-0.20", "0.20-0.80", "0.80-0.95", ">=0.95"]
LIQ_EDGES = [-1.0, 1e3, 1e4, 1e5, np.inf]
LIQ_LABELS = ["<1k", "1k-10k", "10k-100k", ">=100k"]


def round_trip_cost(book: dict, spec: FeeSpec, fee_policy: str = "max_if_unknown",
                    shares: float | None = None) -> dict:
    """Current-book round trip for a hypothetical long-outcome-0 position held to an unchanged
    book (buy sweep then sell sweep on the SAME book): cost per share in probability units and
    its components. Symmetric for outcome 1, so one side suffices (fee is symmetric in p)."""
    rate = resolve_rate(spec, fee_policy)
    b = sweep_fill(book, "buy0", shares, rate, spec.exponent)
    s = sweep_fill(book, "sell0", shares, rate, spec.exponent)
    q = b.shares
    ok = (not b.depth_exhausted) and (not s.depth_exhausted) and b.filled > 0 and s.filled > 0
    if not ok:
        return {"ok": False, "reason": "depth_or_side", "cost_ps": math.nan}
    spread = b.cash - s.cash
    fees = b.fee + s.fee
    hs = b.half_spread_cost + s.half_spread_cost
    imp = b.impact_cost + s.impact_cost
    return {"ok": True, "reason": "", "cost_ps": (spread + fees) / q, "spread_ps": spread / q,
            "half_spread_ps": hs / q, "impact_ps": imp / q, "fee_ps": fees / q,
            "mid": (float(book["best_bid"]) + float(book["best_ask"])) / 2.0}


def breakeven(cost_ps: float, mid: float) -> dict:
    """Edge needed to cover a per-share round-trip cost ``c``.

    Probability terms: the model must move the mid-referenced probability by ``delta = c``
    (expected gross P&L per share = true_prob - mid when the book is unchanged).
    Log-loss terms: with true prob ``m+delta``, the expected log-loss gain over the market price
    is KL ~ delta^2 / (2 m (1-m)) nats per observation (2nd-order; exact KL used for stability)."""
    m = min(max(mid, 1e-6), 1 - 1e-6)
    q = min(max(m + cost_ps, 1e-9), 1 - 1e-9)
    kl = q * math.log(q / m) + (1 - q) * math.log((1 - q) / (1 - m))
    return {"delta_prob": cost_ps, "delta_logloss": kl}


def breakeven_table(df: pd.DataFrame, fee_policy: str = "max_if_unknown") -> pd.DataFrame:
    """Per-market round-trip costs. ``df`` needs sweep book fields (no prefix), ``liquidity`` and
    ``fee_category``/``fee_schedule``/``fees_enabled``. Returns one row per market with regime
    labels, cost components and break-even edges."""
    recs = []
    for r in df.to_dict("records"):
        book = {f: r.get(f) for f in _BOOK_FIELDS}
        if r.get("state") != "two_sided":
            recs.append({"market_id": r.get("market_id"), "ok": False,
                         "reason": str(r.get("state"))})
            continue
        spec = fee_spec(r.get("fee_schedule"), r.get("fees_enabled"), r.get("fee_category"))
        rt = round_trip_cost(book, spec, fee_policy)
        rt["market_id"] = r.get("market_id")
        rt["fee_flag"] = spec.flag
        if rt["ok"]:
            rt.update(breakeven(rt["cost_ps"], rt["mid"]))
        recs.append(rt)
    out = pd.DataFrame(recs).set_index(df.index)
    out["fee_category"] = df["fee_category"].fillna("unknown").astype(str).str.split(":").str[0]
    out["price_band"] = pd.cut(out["mid"], PRICE_BANDS, labels=PRICE_LABELS, right=False)
    out["liq_band"] = pd.cut(pd.to_numeric(df["liquidity"], errors="coerce").fillna(0.0),
                             LIQ_EDGES, labels=LIQ_LABELS)
    return out


def regime_summary(t: pd.DataFrame, by: str) -> pd.DataFrame:
    """Per-regime: n, share with a fillable two-sided 5-share round trip, cost quantiles
    (probability points per share) and the median break-even log-loss gain."""
    g = t.groupby(by, observed=True)
    rows = []
    for k, d in g:
        ok = d[d["ok"] == True]  # noqa: E712
        rows.append({by: k, "n": len(d), "fillable": len(ok) / len(d) if len(d) else math.nan,
                     "cost_p25": ok["cost_ps"].quantile(.25), "cost_med": ok["cost_ps"].median(),
                     "cost_p75": ok["cost_ps"].quantile(.75),
                     "spread_med": ok["spread_ps"].median(), "fee_med": ok["fee_ps"].median(),
                     "impact_med": ok["impact_ps"].median(),
                     "be_ll_med": ok["delta_logloss"].median() if len(ok) else math.nan})
    return pd.DataFrame(rows)


# --- 5. CB4 cost-regime accessors (thin; logic and R0 clamps live in cost_regimes) -----


def cost_regime(on, fee_category, price: float = 0.5, register_path=None) -> dict:
    """Cost terms for a date and fee category (CB4 section 2.9). Never below the CB1 defaults.

    Delegates to ``cost_regimes.cost_regime``; imported lazily because that module imports
    ``cb1_history``, which imports this one. No band map is exposed here.
    """
    from . import cost_regimes

    return cost_regimes.cost_regime(on, fee_category, price, register_path)


def planning_band_map(consumer_declaration: dict, register_path=None) -> dict:
    """The CH52 band map for power planning only (refused when the data window overlaps pmxt)."""
    from . import cost_regimes

    return cost_regimes.planning_band_map(consumer_declaration, register_path)
