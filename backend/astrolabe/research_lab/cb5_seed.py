# ruff: noqa: E501
"""CB5-G: seed-anchor reversion on day-0 slices (CH56), docs/research_lab/CREATIVE_BATCH_5.md section CB5-G and 4.1.

Seed = the last usable pre-first-trade history point (strictly before the first trade, +600 s rule). Feature
``d = VWAP1 - seed`` over ``[t_ft, L + 24h)``; targets use disjoint windows ``E = P_A[t1, t1+6h)`` and ``X = P_A[t3-6h, t3)``.
G1 = slope of ``y = X - E`` on ``d`` (< 0); G2 = a paper maker order at +24h exited at +72h. Attribution: the seed-permutation
placebo on the level-controlled slope (``beta^LC``) and the level-calibrated 0.50-seed stratum rule. The census functions see
only data trimmed to ``[L - 1h, min(first trade + 1h, L + 24h)]`` (``trim_census``); ``window_count`` returns integers only.

Prices are in probability units (1c = 0.01). Pure functions over arrays and frames; no network, no data access.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from . import cb1_history, cost_regimes
from . import cb3_common as C3

POINT_LAG_S = 600
MAX_QUOTE_AGE_S = 7200
H, D = 3600.0, 86400.0
T1_H, T3_H, WIN_H = 24.0, 72.0, 6.0
MIN_LIFE_D = 4.0
MIN_TRADES_PRE = 3
SEED_RANGE = (0.02, 0.98)
TEMPLATE_TOL = 0.0005
D_G2_MIN = 0.03
GEN_H_MIN = 0.025
G2_QUOTE_STEP = 0.01
BIND_COST = 0.0075
FLOOR_G1, FLOOR_G2 = -0.20, 0.010
P_STAGE1 = 0.01
PLACEBO_DRAWS, SEED_PLACEBO = 200, 5161
PLACEBO_MAX_RATE = 0.015
STRATUM_MIN_UNITS = 50
GATE_MIN_UNITS, GATE_MIN_EVENTS, GATE_MIN_DATES = 100, 30, 30
ECHO_STOP_SHARE = 0.50
BOOK_MIN_CHECKABLE, BOOK_MIN_AGREE, BOOK_SPREAD_MAX, BOOK_TOL = 50, 0.75, 0.10, 0.01
SIDE_AUDIT_MIN = 0.75
DETERMINISM_MIN = 0.95
CENSUS_AFTER_TRADE_H = 1.0
CENSUS_BEFORE_H = 1.0
WAYS = ("event", "listing_date")


# ---- price series and trades -------------------------------------------------------------------------------------------


def asof_price(ts: np.ndarray, vals: np.ndarray, t: float) -> float:
    """Latest point usable at ``t`` (stamp + 600 s <= t) and at most 2 h old, else NaN."""
    ts = np.asarray(ts, float)
    i = int(np.searchsorted(ts + POINT_LAG_S, t, side="right")) - 1
    if i < 0 or t - ts[i] > MAX_QUOTE_AGE_S:
        return math.nan
    return float(vals[i])


def seed_points(ts: np.ndarray, vals: np.ndarray, t_ft: float, created: float) -> tuple[np.ndarray, np.ndarray]:
    """``S = {points stamped s with L - 600 <= s and s + 600 <= t_ft}``: usable strictly before the first trade."""
    ts, vals = np.asarray(ts, float), np.asarray(vals, float)
    m = (ts >= created - POINT_LAG_S) & (ts + POINT_LAG_S <= t_ft)
    return ts[m], vals[m]


def seed(ts: np.ndarray, vals: np.ndarray, t_ft: float, created: float) -> dict | None:
    """``{"sigma", "n", "range"}`` (sigma = the latest point of S) or None when S is empty (no valid seed)."""
    st, sv = seed_points(ts, vals, t_ft, created)
    if not len(st):
        return None
    return {"sigma": float(sv[np.argmax(st)]), "n": int(len(st)), "range": float(sv.max() - sv.min()), "t_last": float(st.max()), "t_first": float(st.min())}


def is_template_seed(sigma: float) -> bool:
    return bool(abs(float(sigma) - 0.5) < TEMPLATE_TOL)


def first_trade(tr: pd.DataFrame) -> float | None:
    return float(tr["ts"].min()) if len(tr) else None


def map_token0(tr: pd.DataFrame) -> pd.DataFrame:
    """Token-0 view: ``p0`` (token-1 prices as ``1 - p``), ``ask_side`` (token-0 BUY or token-1 SELL), ``bid_side`` (token-0
    SELL or token-1 BUY). Sorted by ``ts``."""
    if not len(tr):
        return pd.DataFrame({"ts": [], "p0": [], "size": [], "ask_side": [], "bid_side": []})
    idx = tr["outcome_index"].to_numpy().astype(int)
    buy = tr["side"].astype(str).str.upper().to_numpy() == "BUY"
    p = tr["price"].to_numpy(float)
    out = pd.DataFrame({"ts": tr["ts"].to_numpy(float), "p0": np.where(idx == 0, p, 1.0 - p), "size": tr["size"].to_numpy(float),
                        "ask_side": (idx == 0) == buy, "bid_side": (idx == 0) != buy})
    return out.sort_values("ts", kind="stable").reset_index(drop=True)


def vwap(m: pd.DataFrame, a: float, b: float, side: str | None = None) -> float:
    """Size-weighted token-0 price of the prints with ``a <= ts < b`` (``side`` None, ``'ask'`` or ``'bid'``); NaN if empty."""
    s = m[(m["ts"] >= a) & (m["ts"] < b)]
    if side == "ask":
        s = s[s["ask_side"]]
    elif side == "bid":
        s = s[s["bid_side"]]
    w = s["size"].to_numpy(float)
    return float((s["p0"].to_numpy(float) * w).sum() / w.sum()) if len(s) and w.sum() > 0 else math.nan


def window_count(tr: pd.DataFrame, a: float, b: float) -> int:
    """Count-only accessor (census G-vii): the number of prints with ``a <= ts < b``. Never a price, size or side."""
    return int(((tr["ts"] >= a) & (tr["ts"] < b)).sum()) if len(tr) else 0


# ---- population and units ----------------------------------------------------------------------------------------------


def h_gen(price: float, regime: dict | None = None) -> float:
    hs = regime["half_spread"] if regime else cb1_history.half_spread(float(price))
    return max(float(hs), GEN_H_MIN)


def listing_date(created: float) -> str:
    return datetime.fromtimestamp(created, UTC).strftime("%Y-%m-%d")


def iso_week(created: float) -> str:
    c = datetime.fromtimestamp(created, UTC).isocalendar()
    return f"{c[0]}-W{c[1]:02d}"


def g_unit(rec: dict, ts: np.ndarray, vals: np.ndarray, tr: pd.DataFrame, truncated: bool, oldest_ts, *, stage: str = "h2",
           clock: float | None = None, regime=cost_regimes.cost_regime) -> tuple[dict | None, str, dict | None]:
    """One market -> ``(unit, reason, truncated_unit)``. ``rec``: ``market_id, event_id, fee_category, created (epoch),
    end (epoch), close (epoch or NaN), y0 (final YES payout or NaN), negrisk_members, stratum``. Every exclusion has a
    reason (counted by the caller). Uses ``created`` and ``end`` only (scheduled facts); an early close never changes
    inclusion: the exit price is then the payout. ``truncated_unit`` (history-price feature and target) is returned for
    markets excluded because trades are truncated before L, for the truncation worst case."""
    L = float(rec["created"])
    t1, t3 = L + T1_H * H, L + T3_H * H
    cat = rec.get("fee_category", "")
    if str(cat) == "weather":
        return None, "weather", None
    if int(rec.get("negrisk_members", 0) or 0) > 2:
        return None, "negrisk_multi", None
    end = float(rec.get("end", math.nan))
    if not math.isfinite(end):
        return None, "end_unknown", None
    if end - L < MIN_LIFE_D * D:
        return None, "life_lt_4d", None
    if stage == "h2" and (clock is None or L + 4 * D + H > clock):
        return None, "after_h2_clock", None
    m = map_token0(tr)
    if truncated and (oldest_ts is None or float(oldest_ts) > L):
        return None, "trades_truncated_before_L", _truncated_unit(rec, ts, vals, oldest_ts, L, t1, t3)
    pre = m[(m["ts"] >= L) & (m["ts"] < t1)]
    if len(pre) < MIN_TRADES_PRE:
        return None, "lt3_trades", None
    t_ft = float(pre["ts"].iloc[0])
    sd = seed(ts, vals, t_ft, L)
    if sd is None:
        return None, "no_seed", None
    sigma = sd["sigma"]
    if not (SEED_RANGE[0] <= sigma <= SEED_RANGE[1]):
        return None, "seed_extreme", None
    v1 = vwap(m, t_ft, t1)
    e_a, e_b = vwap(m, t1, t1 + WIN_H * H, "ask"), vwap(m, t1, t1 + WIN_H * H, "bid")
    close = float(rec.get("close", math.nan))
    y0 = float(rec.get("y0", math.nan))
    early = math.isfinite(close) and close < t3
    if early:
        x_a = x_b = y0
        if not math.isfinite(y0):
            return None, "payout_unknown", None
    else:
        x_a, x_b = vwap(m, t3 - WIN_H * H, t3, "ask"), vwap(m, t3 - WIN_H * H, t3, "bid")
    if not math.isfinite(e_a):
        return None, "E_unavailable", None
    if not math.isfinite(x_a):
        return None, "X_unavailable", None
    p_t1 = asof_price(ts, vals, t1)
    p_e = asof_price(ts, vals, t1 + WIN_H * H)
    p_t3 = asof_price(ts, vals, t3)
    path = np.asarray(vals, float)[(np.asarray(ts, float) + POINT_LAG_S > t1) & (np.asarray(ts, float) + POINT_LAG_S <= t3)]
    ask_prints = m[(m["ts"] > t1) & (m["ts"] <= t1 + T1_H * H) & m["ask_side"]][["ts", "p0"]]
    bid_prints = m[(m["ts"] > t1) & (m["ts"] <= t1 + T1_H * H) & m["bid_side"]][["ts", "p0"]]
    unit = {"market_id": str(rec["market_id"]), "event": str(rec.get("event_id") or rec["market_id"]), "fee_category": cat,
            "sports": cb1_history.is_sports(cat), "created": L, "listing_date": listing_date(L), "iso_week": iso_week(L),
            "stratum": str(rec.get("stratum", "")), "t_ft": t_ft, "t_ft_minus_L": t_ft - L, "sigma": sigma, "seed_n": sd["n"], "seed_range": sd["range"],
            "seed_gap_min": (t_ft - sd["t_last"]) / 60.0, "informative": not is_template_seed(sigma), "template": is_template_seed(sigma),
            "vwap1": v1, "d": v1 - sigma, "E": e_a, "X": x_a, "y": x_a - e_a, "early_close": bool(early),
            "y_B": (x_b - e_b) if math.isfinite(e_b) and math.isfinite(x_b) else math.nan,
            "y_H": (p_t3 - p_e) if math.isfinite(p_t3) and math.isfinite(p_e) else math.nan,
            "p_t1": p_t1, "p_t3": p_t3, "early_payout": y0 if early else math.nan, "path": path, "ask_prints": ask_prints, "bid_prints": bid_prints}
    return unit, "ok", None


def _truncated_unit(rec: dict, ts, vals, oldest_ts, L: float, t1: float, t3: float) -> dict | None:
    """History-price-only unit for a market whose trades are truncated before L (truncation worst case)."""
    if oldest_ts is None:
        return None
    sd = seed(ts, vals, float(oldest_ts), L)
    p_t1, p_e, p_t3 = asof_price(ts, vals, t1), asof_price(ts, vals, t1 + WIN_H * H), asof_price(ts, vals, t3)
    if sd is None or not all(math.isfinite(x) for x in (p_t1, p_e, p_t3)):
        return None
    return {"market_id": str(rec["market_id"]), "event": str(rec.get("event_id") or rec["market_id"]), "listing_date": listing_date(L),
            "d": p_t1 - sd["sigma"], "y": p_t3 - p_e, "informative": not is_template_seed(sd["sigma"]), "p_t1": p_t1, "p_t3": p_t3, "sigma": sd["sigma"],
            "created": L, "fee_category": rec.get("fee_category", ""), "hist_ts": np.asarray(ts, float), "hist_vals": np.asarray(vals, float)}


def units_frame(units: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(units) if units else pd.DataFrame(columns=["market_id", "event", "listing_date", "d", "y", "informative"])


def primary(df: pd.DataFrame) -> pd.DataFrame:
    """Primary population: non-sports (sports is a reported, uncounted stratum), informative seeds."""
    return df[(~df["sports"].astype(bool)) & df["informative"].astype(bool)].reset_index(drop=True)


def _ways(df: pd.DataFrame) -> dict[str, np.ndarray]:
    return {"event": df["event"].astype(str).to_numpy(), "listing_date": df["listing_date"].astype(str).to_numpy()}


# ---- G1 ---------------------------------------------------------------------------------------------------------------


def g1_slope(df: pd.DataFrame, *, y: str = "y", n_boot: int = 2000, seed_: int = 516) -> dict:
    """OLS slope of ``y`` on ``d`` (intercept) over the informative-seed units; one-sided p for beta < 0 = max over event and
    listing date (small-G rule on both)."""
    if not len(df):
        return {"testable": False, "p": 1.0, "n": 0, "reason": ["no units"]}
    return C3.slope_test(df[y].to_numpy(float), df["d"].to_numpy(float), None, _ways(df), sign=-1, small_g_ways=WAYS, n_boot=n_boot, seed=seed_)


def _level_cols(df: pd.DataFrame) -> np.ndarray:
    v = df["vwap1"].to_numpy(float)
    return np.column_stack([v, np.abs(v - 0.5)])


def g1_level_controlled(df: pd.DataFrame, *, y: str = "y", n_boot: int = 2000, seed_: int = 516) -> dict:
    """``beta^LC``: the G1 slope with ``VWAP1`` and ``|VWAP1 - 0.5|`` as covariates (identified only from variation of the seed at
    a given first-day level)."""
    if not len(df):
        return {"testable": False, "p": 1.0, "n": 0, "reason": ["no units"]}
    return C3.slope_test(df[y].to_numpy(float), df["d"].to_numpy(float), _level_cols(df), _ways(df), sign=-1, small_g_ways=WAYS, n_boot=n_boot, seed=seed_)


def g1_stratum_adjusted(df: pd.DataFrame, *, min_stratum: int = 5, n_boot: int = 0) -> dict:
    """G1 slope with the h2 draw strata as fixed effects (strata with fewer than ``min_stratum`` units pooled)."""
    if not len(df):
        return {"testable": False, "p": 1.0, "n": 0, "reason": ["no units"]}
    s = df["stratum"].astype(str)
    cnt = s.map(s.value_counts())
    s = s.where(cnt >= min_stratum, "other")
    Z = pd.get_dummies(s, drop_first=True).to_numpy(float)
    return C3.slope_test(df["y"].to_numpy(float), df["d"].to_numpy(float), Z if Z.size else None, _ways(df), sign=-1, small_g_ways=WAYS, n_boot=n_boot)


def stage1_advance_g1(res: dict) -> bool:
    """The Stage-1 core gate for a slope result: testable, p < 0.01, beta <= -0.20."""
    return bool(res.get("testable") and res["p"] < P_STAGE1 and res["beta"] <= FLOOR_G1)


def _ols_slope(y: np.ndarray, x: np.ndarray) -> float:
    xc = x - x.mean()
    sxx = float((xc**2).sum())
    return float((xc * (y - y.mean())).sum() / sxx) if sxx > 0 else math.nan


def seed_permutation_placebo(df: pd.DataFrame, *, n_draws: int = PLACEBO_DRAWS, seed_: int = SEED_PLACEBO, slope: str = "level_controlled") -> dict:
    """Each informative market's seed is replaced by another market's seed drawn without replacement within
    ``fee_category`` x listing ISO week; the full Stage-1 gate is recomputed on ``beta^LC`` (binding) and on the raw slope
    (reported). Calibration: the advance rate must be at most 1.5%. A group of one market keeps its own seed."""
    rng = np.random.default_rng(seed_)
    groups = list(df.groupby([df["fee_category"].astype(str), df["iso_week"].astype(str)]).indices.values())
    sigma0 = df["sigma"].to_numpy(float)
    v1 = df["vwap1"].to_numpy(float)
    adv_lc = adv_raw = 0
    for _ in range(n_draws):
        sig = sigma0.copy()
        for g in groups:
            if len(g) > 1:
                sig[g] = sigma0[rng.permutation(g)]
        pdf = df.assign(sigma=sig, d=v1 - sig)
        adv_lc += int(stage1_advance_g1(g1_level_controlled(pdf, n_boot=0)))
        adv_raw += int(stage1_advance_g1(g1_slope(pdf, n_boot=0)))
    key = adv_lc if slope == "level_controlled" else adv_raw
    return {"n_draws": n_draws, "slope": slope, "advance_rate": key / n_draws, "advance_rate_level_controlled": adv_lc / n_draws,
            "advance_rate_raw": adv_raw / n_draws, "max_rate": PLACEBO_MAX_RATE, "ok": bool(key / n_draws <= PLACEBO_MAX_RATE)}


def template_stratum(df: pd.DataFrame, beta_inf: float) -> dict:
    """Level-calibrated 0.50-seed rule (attribution, binding). Fit ``y = a + g*VWAP1 + dl*|VWAP1-0.5|`` on the 0.50 stratum;
    residualise the informative units inside the stratum's 5th-95th percentile range of VWAP1 (no extrapolation); take the slope
    of the residual on ``d``. Credited only if the stratum has >= 50 units and ``beta^{|0.5} <= beta_inf / 2`` (declared sign
    negative, at least half the magnitude). Below 50 units: ``unverified``; otherwise a failed (b): ``generic_first_day_reversal``."""
    tpl = df[df["template"].astype(bool) & ~df["sports"].astype(bool)]
    inf = df[df["informative"].astype(bool) & ~df["sports"].astype(bool)]
    out = {"n_template": int(len(tpl)), "n_informative": int(len(inf)), "beta_informative": beta_inf}
    if len(tpl) < STRATUM_MIN_UNITS:
        return {**out, "status": "unverified", "credited": False, "reason": f"0.50 stratum has {len(tpl)} < {STRATUM_MIN_UNITS} units"}
    X = np.column_stack([np.ones(len(tpl)), _level_cols(tpl)])
    coef, *_ = np.linalg.lstsq(X, tpl["y"].to_numpy(float), rcond=None)
    lo, hi = np.percentile(tpl["vwap1"].to_numpy(float), [5, 95])
    inside = inf[(inf["vwap1"] >= lo) & (inf["vwap1"] <= hi)]
    out.update(n_inside_range=int(len(inside)), n_outside_range=int(len(inf) - len(inside)), level_fit=[float(c) for c in coef])
    if len(inside) < 3:
        return {**out, "status": "unverified", "credited": False, "reason": "no informative units inside the stratum range"}
    resid = inside["y"].to_numpy(float) - np.column_stack([np.ones(len(inside)), _level_cols(inside)]) @ coef
    b_res = _ols_slope(resid, inside["d"].to_numpy(float))
    b_tpl = _ols_slope(tpl["y"].to_numpy(float), tpl["d"].to_numpy(float))
    ok = bool(math.isfinite(b_res) and math.isfinite(beta_inf) and b_res < 0 and b_res <= beta_inf / 2.0)
    return {**out, "beta_residual": b_res, "beta_template_raw_reported": b_tpl, "raw_comparison_reported": bool(b_tpl <= beta_inf / 2.0),
            "status": "credited" if ok else "generic_first_day_reversal", "credited": ok}


# ---- G2 ---------------------------------------------------------------------------------------------------------------


def _fee_ps(rate: float, a: float) -> float:
    return rate * a * (1.0 - a)


def g2_orders(df: pd.DataFrame, *, regime=cost_regimes.cost_regime, bind: float = 0.0) -> pd.DataFrame:
    """Paper maker orders for informative units with ``|d| >= 3c``: placed at t1 on the seed side (ask if the price rose above
    the seed, bid if it fell) at ``q = min(p(t1) + h_gen + 1c, 0.99)`` / ``max(p(t1) - h_gen - 1c, 0.01)``; filled at q only on
    a strict trade-through in ``(t1, t1+24h]`` (an ask-side print above q, a bid-side print below q); exit at t3 as a taker
    (``a_x = min(p(t3) + h_gen, 0.999)`` / ``b_x = max(p(t3) - h_gen, 0.001)``, or the payout if the market closed before t3),
    plus ``bind`` on the exit price. ``net`` includes the taker fee on the exit and the R2 adverse-selection term for fills
    before the category's rollout date. Unfilled and unavailable units are kept with ``filled`` False."""
    rows = []
    for _, u in df.iterrows():
        if not u["informative"] or abs(u["d"]) < D_G2_MIN or not math.isfinite(u["p_t1"]):
            continue
        t1 = u["created"] + T1_H * H
        ask = u["d"] > 0
        rg = regime(datetime.fromtimestamp(t1, UTC).date(), u["fee_category"], u["p_t1"])
        h = h_gen(u["p_t1"], rg)
        q = min(u["p_t1"] + h + G2_QUOTE_STEP, 0.99) if ask else max(u["p_t1"] - h - G2_QUOTE_STEP, 0.01)
        pr = u["ask_prints"] if ask else u["bid_prints"]
        hit = pr[pr["p0"] > q] if ask else pr[pr["p0"] < q]
        rec = {"market_id": u["market_id"], "event": u["event"], "listing_date": u["listing_date"], "iso_week": u["iso_week"],
               "side": "ask" if ask else "bid", "q": q, "filled": bool(len(hit)), "fee_category": u["fee_category"], "net": math.nan}
        if len(hit):
            t_fill = float(hit["ts"].iloc[0])
            fr = regime(datetime.fromtimestamp(t_fill, UTC).date(), u["fee_category"], q)
            if math.isfinite(u["early_payout"]):
                x = float(u["early_payout"])
            elif math.isfinite(u["p_t3"]):
                hx = h_gen(u["p_t3"], regime(datetime.fromtimestamp(u["created"] + T3_H * H, UTC).date(), u["fee_category"], u["p_t3"]))
                x = min(u["p_t3"] + hx, 0.999) if ask else max(u["p_t3"] - hx, 0.001)
            else:
                x = math.nan
            if math.isfinite(x):
                x = min(x + bind, 0.999) if ask else max(x - bind, 0.001)
                a_as = fr["a_as_cents"] / 100.0
                rate = fr["fee_rate"]
                net = (q - x - _fee_ps(rate, x) - a_as) if ask else (x - q - _fee_ps(rate, x) - a_as)
                rec.update(net=net, capital=(1.0 - q) if ask else q, hold_days=max((u["created"] + T3_H * H - t_fill) / D, 1.0),
                           post_rollout=bool(fr["post_rollout"]), era_rule=fr["era_rule"], t_fill=t_fill)
            else:
                rec["filled"] = False
                rec["reason"] = "exit_unavailable"
        rows.append(rec)
    return pd.DataFrame(rows)


def g2_test(orders: pd.DataFrame, *, n_boot: int = 2000) -> dict:
    """Mean net per filled share > 0 (one-sided), p = max over event and listing date (small-G rule on both)."""
    f = orders[orders["filled"] & orders["net"].notna()] if len(orders) else orders
    n_all = int(len(orders))
    if not len(f):
        return {"testable": False, "p": 1.0, "n": 0, "n_orders": n_all, "reason": ["no fills"], "size_only": True}
    ways = {"event": f["event"].astype(str).to_numpy(), "listing_date": f["listing_date"].astype(str).to_numpy()}
    out = C3.mean_test(f["net"].to_numpy(float), ways, sign=1, small_g_ways=WAYS, n_boot=n_boot)
    out["n_orders"] = n_all
    out["fill_rate"] = float(len(f) / n_all) if n_all else math.nan
    out["r_ann"] = float(365.0 * f["net"].sum() / (f["capital"] * f["hold_days"]).sum()) if (f["capital"] * f["hold_days"]).sum() > 0 else math.nan
    if not out.get("testable"):
        out["size_only"] = bool(len(f) < C3.D.MIN_UNITS or any("clusters" in r for r in out.get("reason", [])))
    return out


def stage1_advance_g2(res: dict) -> bool:
    return bool(res.get("testable") and res["p"] < P_STAGE1 and res["mean"] >= FLOOR_G2 and (res.get("r_ann") or 0.0) >= 0.10)


def breakeven_placebo_g2(df: pd.DataFrame, *, n_draws: int = PLACEBO_DRAWS, seed_: int = SEED_PLACEBO + 1, regime=cost_regimes.cost_regime) -> dict:
    """Fill prices kept; the exit price of each filled order is a random point of that market's own as-of path in [t1, t3] (the
    path permuted within market), shifted so that the expected net is exactly 0 for every order. The full Stage-1 gate is rerun on
    200 draws; the advance rate must be at most 1.5%."""
    base = g2_orders(df, regime=regime)
    f = base[base["filled"] & base["net"].notna()]
    if len(f) < 2:
        return {"n_draws": 0, "advance_rate": None, "ok": True, "note": "no filled orders"}
    paths = {r["market_id"]: np.asarray(r["path"], float) for _, r in df.iterrows()}
    rng = np.random.default_rng(seed_)
    ways = {"event": f["event"].astype(str).to_numpy(), "listing_date": f["listing_date"].astype(str).to_numpy()}
    adv = 0
    for _ in range(n_draws):
        v = np.empty(len(f))
        for i, (_, o) in enumerate(f.iterrows()):
            pa = paths.get(o["market_id"], np.array([]))
            if not len(pa):
                v[i] = 0.0
                continue
            ask = o["side"] == "ask"
            cost_pts = np.minimum(pa + GEN_H_MIN, 0.999) if ask else np.maximum(pa - GEN_H_MIN, 0.001)
            sign = -1.0 if ask else 1.0
            v[i] = sign * (cost_pts[int(rng.integers(0, len(pa)))] - cost_pts.mean())
        res = C3.mean_test(v, ways, sign=1, small_g_ways=WAYS, n_boot=0)
        adv += int(bool(res.get("testable") and res["p"] < P_STAGE1 and res["mean"] >= FLOOR_G2))
    rate = adv / n_draws
    return {"n_draws": n_draws, "n_advanced": adv, "advance_rate": rate, "max_rate": PLACEBO_MAX_RATE, "ok": bool(rate <= PLACEBO_MAX_RATE)}


def carry_rule(g1_advanced: bool, g2: dict) -> dict:
    """G2 carry: if G1 advances and G2 is not testable for size only (fills < 100 or fill clusters < 30) with a point estimate
    >= 0, G2 enters Stage 2 as carried, untested at Stage 1. A G2 that was testable and failed is not carried."""
    carried = bool(g1_advanced and not g2.get("testable") and g2.get("size_only") and (g2.get("mean") is not None and g2["mean"] >= 0 and not math.isnan(g2["mean"])))
    return {"carried": carried, "g1_advanced": bool(g1_advanced), "g2_testable": bool(g2.get("testable")), "g2_size_only": bool(g2.get("size_only"))}


def era_subset_rule(units_or_orders: pd.DataFrame, value_col: str, register_path=None) -> dict:
    """If the register's ``era_rule`` is ``post_rollout_or_interaction``, the post-rollout subset (L on or after the category's
    ``era_window_start``) must have the declared sign; returns ``{"required", "ok"}``. ``value_col`` is the per-row value whose
    sign is declared (G1 targets a negative slope on the subset; G2 a positive mean)."""
    rg = cost_regimes.cost_regime("2026-10-01", "other", 0.5, register_path)
    if rg["era_rule"] != cost_regimes.ERA_RULE_POST:
        return {"required": False, "ok": True, "era_rule": rg["era_rule"]}
    sub = units_or_orders[[datetime.fromtimestamp(r["created"], UTC).date() >= cost_regimes.era_window_start(r["fee_category"])
                           for _, r in units_or_orders.iterrows()]] if "created" in units_or_orders else units_or_orders
    if value_col == "slope":
        v = _ols_slope(sub["y"].to_numpy(float), sub["d"].to_numpy(float)) if len(sub) > 2 else math.nan
        ok = bool(math.isfinite(v) and v < 0)
    else:
        v = float(sub[value_col].mean()) if len(sub) else math.nan
        ok = bool(math.isfinite(v) and v > 0)
    return {"required": True, "ok": ok, "post_rollout_value": v, "n_post": int(len(sub)), "era_rule": rg["era_rule"]}


def truncation_worst_case_g(df: pd.DataFrame, truncated: list[dict]) -> dict:
    """Truncated markets added back with the history-price feature and target (``y_H``); the G1 slope must stay negative."""
    add = pd.DataFrame([t for t in truncated if t and t.get("informative")])
    if not len(add):
        return {"n_added": 0, "ok": True, "beta": None}
    both = pd.concat([df[["d", "y"]], add[["d", "y"]]], ignore_index=True)
    b = _ols_slope(both["y"].to_numpy(float), both["d"].to_numpy(float))
    return {"n_added": int(len(add)), "beta": b, "ok": bool(math.isfinite(b) and b < 0)}


# ---- census (counts and gates only; no target, no coefficient) ---------------------------------------------------------


def trim_census(ts: np.ndarray, vals: np.ndarray, tr: pd.DataFrame, created: float) -> tuple[np.ndarray, np.ndarray, pd.DataFrame, float]:
    """The only view census code may use: price points in ``[L - 1h, bound]`` and trades with ``ts <= bound`` where ``bound =
    min(first trade + 1h, L + 24h)`` (the first trade being the first at or after L). Anything later is dropped here."""
    m = tr[tr["ts"] >= created] if len(tr) else tr
    ft = first_trade(m)
    bound = created + T1_H * H if ft is None else min(ft + CENSUS_AFTER_TRADE_H * H, created + T1_H * H)
    ts, vals = np.asarray(ts, float), np.asarray(vals, float)
    k = (ts >= created - CENSUS_BEFORE_H * H) & (ts <= bound)
    return ts[k], vals[k], (tr[tr["ts"] <= bound] if len(tr) else tr), bound


def census_market(rec: dict, ts: np.ndarray, vals: np.ndarray, tr: pd.DataFrame) -> dict:
    """G-i..G-iii facts for one market from the trimmed view only: first trade, seed validity, sigma, echo flag, template flag."""
    L = float(rec["created"])
    ts, vals, trt, bound = trim_census(ts, vals, tr, L)
    if len(ts):
        assert float(ts.max()) <= bound  # no price after the census bound can be seen
    m = map_token0(trt[trt["ts"] >= L] if len(trt) else trt)
    out = {"market_id": str(rec["market_id"]), "has_trade": bool(len(m)), "valid_seed": False, "sigma": math.nan, "echo": False, "template": False,
           "minutes_to_first_trade": math.nan, "bound": bound}
    if not len(m):
        return out
    t_ft = float(m["ts"].iloc[0])
    sd = seed(ts, vals, t_ft, L)
    if sd is None:
        return out
    out.update(valid_seed=True, sigma=sd["sigma"], echo=bool(abs(float(m["p0"].iloc[0]) - sd["sigma"]) < TEMPLATE_TOL),
               template=is_template_seed(sd["sigma"]), minutes_to_first_trade=(t_ft - sd["t_first"]) / 60.0, first_trade_p0=float(m["p0"].iloc[0]),
               t_ft=t_ft)
    return out


def seed_echo_share(facts: list[dict]) -> dict:
    """G-ii: share of valid seeds equal to the first trade's token-0 price; more than 50% -> CB5-G stops before the freeze."""
    v = [f for f in facts if f["valid_seed"]]
    share = float(np.mean([f["echo"] for f in v])) if v else math.nan
    return {"n_valid": len(v), "share_echo": share, "stop": bool(v and share > ECHO_STOP_SHARE)}


def determinism_share(a: dict[float, float], b: dict[float, float]) -> dict:
    """G-iv: on points stamped in both the stored series and the refetch, the share identical (|diff| < 0.0005)."""
    common = sorted(set(a) & set(b))
    if not common:
        return {"n_overlap": 0, "share_identical": math.nan, "disclosed": False}
    s = float(np.mean([abs(a[t] - b[t]) < TEMPLATE_TOL for t in common]))
    return {"n_overlap": len(common), "share_identical": s, "disclosed": bool(s < DETERMINISM_MIN)}


def seed_book_agreement(markets: list[dict]) -> dict:
    """G-v. ``markets``: ``{"sigma", "t_ft", "first_seen_ts", "bid", "ask"}`` from the census cohort. Checkable = first sighting
    before the first trade with a two-sided touch of spread <= 0.10; agreement = |sigma - mid| <= 0.01. Gate: >= 50 checkable and
    >= 75% agreement; below 75% -> ``fail`` (CB5-G stops before the freeze); fewer than 50 checkable -> ``unverified``."""
    chk, agree = 0, 0
    for m in markets:
        if not (math.isfinite(m["first_seen_ts"]) and m["first_seen_ts"] < m["t_ft"]):
            continue
        b, a = m["bid"], m["ask"]
        if not (math.isfinite(b) and math.isfinite(a) and 0 < b < a < 1 and a - b <= BOOK_SPREAD_MAX):
            continue
        chk += 1
        agree += int(abs(m["sigma"] - (a + b) / 2.0) <= BOOK_TOL)
    share = agree / chk if chk else math.nan
    if chk < BOOK_MIN_CHECKABLE:
        status = "unverified"
    else:
        status = "pass" if share >= BOOK_MIN_AGREE else "fail"
    return {"n_checkable": chk, "n_agree": agree, "agreement": share, "status": status, "stop": status == "fail"}


def side_audit_day0(per_market: list[tuple[np.ndarray, np.ndarray, pd.DataFrame, float]]) -> dict:
    """G-vi on day-0 trades (feature window ``[L, L+24h)`` only). Per token, the share of BUY prints at or above the as-of history
    price of that token, and of SELL prints at or below it; each must be >= 75%. ``per_market``: ``(ts, vals, trades, L)``."""
    cnt = {(tok, s): [0, 0] for tok in (0, 1) for s in ("BUY", "SELL")}
    for ts, vals, tr, L in per_market:
        w = tr[(tr["ts"] >= L) & (tr["ts"] < L + T1_H * H)] if len(tr) else tr
        for _, r in w.iterrows():
            p0 = asof_price(ts, vals, float(r["ts"]))
            if not math.isfinite(p0):
                continue
            tok = int(r["outcome_index"])
            ref = p0 if tok == 0 else 1.0 - p0
            side = str(r["side"]).upper()
            if side not in ("BUY", "SELL"):
                continue
            ok = float(r["price"]) >= ref - 1e-12 if side == "BUY" else float(r["price"]) <= ref + 1e-12
            c = cnt[(tok, side)]
            c[0] += int(ok)
            c[1] += 1
    shares = {f"token{t}_{s.lower()}": (c[0] / c[1] if c[1] else math.nan) for (t, s), c in cnt.items()}
    n = {f"token{t}_{s.lower()}": c[1] for (t, s), c in cnt.items()}
    ok = all(math.isfinite(v) and v >= SIDE_AUDIT_MIN for v in shares.values())
    return {"shares": shares, "n": n, "ok": bool(ok), "stop": not ok}


def g56_gate(df: pd.DataFrame, n_both_windows: int | None = None) -> dict:
    """G-vii: >= 100 informative-seed units with both entry and exit windows non-empty, >= 30 events and >= 30 listing dates."""
    inf = df[df["informative"].astype(bool) & ~df["sports"].astype(bool)] if len(df) else df
    n = int(len(inf)) if n_both_windows is None else int(n_both_windows)
    ev = int(inf["event"].nunique()) if len(inf) else 0
    dt = int(inf["listing_date"].nunique()) if len(inf) else 0
    ok = bool(n >= GATE_MIN_UNITS and ev >= GATE_MIN_EVENTS and dt >= GATE_MIN_DATES)
    return {"n_units": n, "n_events": ev, "n_dates": dt, "ok": ok,
            "n_abs_d_ge_3c": int((inf["d"].abs() >= D_G2_MIN).sum()) if len(inf) else 0, "n_template": int(df["template"].sum()) if len(df) else 0}


def truncation_worst_case_g2(orders: pd.DataFrame, truncated: list[dict], *, regime=cost_regimes.cost_regime) -> dict:
    """Truncated markets with ``|d_H| >= 3c`` (history-price feature) are added back; the fill is decided on history prices crossing
    ``q`` in ``(t1, t1+24h]`` (a point strictly beyond q on the order side) and the exit at the history price at t3. The mean net
    of the combined orders must stay positive (the declared side)."""
    nets = [float(x) for x in orders["net"].dropna()] if len(orders) and "net" in orders else []
    added = 0
    for t in truncated:
        if not t or not t.get("informative") or abs(t["d"]) < D_G2_MIN or not math.isfinite(t.get("p_t1", math.nan)) or not math.isfinite(t.get("p_t3", math.nan)):
            continue
        t1 = t["created"] + T1_H * H
        ask = t["d"] > 0
        rg = regime(datetime.fromtimestamp(t1, UTC).date(), t.get("fee_category", ""), t["p_t1"])
        q = min(t["p_t1"] + h_gen(t["p_t1"], rg) + G2_QUOTE_STEP, 0.99) if ask else max(t["p_t1"] - h_gen(t["p_t1"], rg) - G2_QUOTE_STEP, 0.01)
        hts, hv = t["hist_ts"], t["hist_vals"]
        m = (hts > t1) & (hts <= t1 + T1_H * H)
        hit = (hv[m] > q).any() if ask else (hv[m] < q).any()
        if not hit:
            continue
        hx = h_gen(t["p_t3"], rg)
        x = min(t["p_t3"] + hx, 0.999) if ask else max(t["p_t3"] - hx, 0.001)
        nets.append((q - x - _fee_ps(rg["fee_rate"], x) - rg["a_as_cents"] / 100.0) if ask else (x - q - _fee_ps(rg["fee_rate"], x) - rg["a_as_cents"] / 100.0))
        added += 1
    mean = float(np.mean(nets)) if nets else math.nan
    return {"n_added": added, "mean": mean, "ok": bool(not nets or (math.isfinite(mean) and mean > 0)) if added else True}
