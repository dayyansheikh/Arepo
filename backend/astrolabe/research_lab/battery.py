"""Hypothesis battery 1 (HB1): 72 pre-declared hypotheses on the h2_main historical panel.

EXPLORATORY_HISTORICAL development screen. Governance (``FEATURE_DISCOVERY_PROGRAMME.md`` s. 3):
one revision, one discovery/judgement time split (``SPLIT_TS``, 24h embargo on both sides), every
hypothesis declared in ``HYPOTHESES`` and in ``docs/research_lab/HYPOTHESIS_BATTERY_1.md`` before
any outcome is computed, Benjamini-Yekutieli at q = 0.10 over the cumulative test count. Nothing
here is prospective evidence, a confirmation, or an edge, calibration or profitability claim.

Two test statistics:

* ``beta``: OLS of the future mid change ``d_h`` (or resolution excess) on one declared feature and
  declared controls, fitted on judgement rows. The tested sign is the sign of the same regression
  on discovery rows (theory prior when discovery is not testable). p is one-sided from the
  cluster-robust z, taking the larger of the event-clustered and the two-way (event x UTC day)
  clustered p.
* ``dll``: incremental out-of-sample log loss of LightGBM(M0v + feature) against LightGBM(M0v),
  both fitted on discovery rows with the fixed ``ml_explain.lgb_fit`` configuration and scored on
  judgement rows. p is one-sided for mean ΔLL > 0, same clustering rule.

Feature clocks: price-path features use 10-minute points stamped ``s`` with ``s + 600 < t``. Every
trade-based battery feature uses trades with ``ts < s_last``, the stamp of the last usable price
point (price-aligned window), so a trade is never newer than the price it is compared with.
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

from . import battery_data as bd
from . import economics, ml_explain, ml_models, provenance
from . import history_backfill as hb

VERSION = "hb1-v1"
REVISION = "hb1_battery"
EVIDENCE_ROLE = "exploratory_historical"
TRIAL_KIND = "history_battery"
SPLIT_TS = 1782864000.0  # 2026-07-01T00:00:00Z
EMBARGO_S = 86400.0  # = the longest horizon; applied on both sides of the split
LAG = float(hb.POINT_LAG_S)  # 600 s
MAX_AGE = float(hb.MAX_QUOTE_AGE_S)  # 7200 s
H = 3600.0
DAY = 86400.0
LARGE_USD = 500.0
SMALL_USD = 50.0
CONVEX_USD = 1000.0
CONVEX_P = 0.20
FRESH_S = 7 * DAY
NEW1D_S = DAY
AGG_MIN = 0.01
REC_K = 3.0  # shrinkage pseudo-markets at edge 0
REC_MIN_MARKETS = 2
REC_EDGE = 0.05
REC_DELAY_S = 2 * DAY  # a market's outcome counts as known 2 days after closedTime
MOVE_BIG = 0.01
MIN_JUDGE_ROWS = 300
MIN_JUDGE_CLUSTERS = 30
MIN_NONZERO_ROWS = 100
MIN_NONZERO_CLUSTERS = 20
MIN_DISC_ROWS_DLL = 2000
N_BOOT = 2000
SEED = 116
BY_Q = 0.10
LGB_ROUNDS = 100
LADDER_MIN_LEFT_S = 2 * DAY
LADDER_Z_STEPS = 56  # 14 days of 6h steps
LADDER_Z_MIN = 8
NR_SUM_MAX_AGE = MAX_AGE
NO_FEE_CATEGORIES = ("unknown", "other:zero_fees")

M0V = (
    *ml_models.M0_FEATURES,
    "ml_own_vol",
    "ml_rv_2h",
    "ml_rv_6h",
    "ml_rv_1d",
    "ml_rv_7d",
    "ml_log_hours_to_end",
    "ml_dist_01",
    "ml_tf_n_24h",
    "ml_tf_log_notional_24h",
)
C0 = (
    "ml_logit_mid",
    "ml_abs_mid_dev",
    "c_chg_1h",
    "c_chg_1d",
    "c_chg_1w",
    "ml_chg_1h_missing",
    "ml_chg_1d_missing",
    "ml_chg_1w_missing",
    "c_dprev",
    "c_dprev_missing",
)
C0M = tuple(c for c in C0 if c not in ("ml_logit_mid", "ml_abs_mid_dev"))  # momentum only
# EXECUTION_COSTS.md median spread by price band (sweep 20261011T184657Z), probability units
BAND_SPREAD = ((0.05, 0.041), (0.20, 0.030), (0.80, 0.022), (0.95, 0.030), (1.01, 0.025))
PRIOR_KIND_ONE = (
    "flow_screen",
    "leadlag_screen",
    "comparison",
    "detector_eval",
    "detector_eval_if_h1",
    "e007_staleness_dev",
    "calibration_study_c1",
    "dev_fit",
)

PANEL_COLS = [
    "market_id",
    "event_id",
    "t_i",
    "mid_i",
    "fee_category",
    "status",
    "traded_before_t",
    *ml_models.M0_FEATURES,
    "ml_own_dmid_prev",
    "ml_own_vol",
    "ml_rv_2h",
    "ml_rv_6h",
    "ml_rv_1d",
    "ml_rv_7d",
    "ml_log_hours_to_end",
    "ml_dist_01",
    "ml_tf_n_24h",
    "ml_tf_log_notional_24h",
    "ml_market_age_h",
]
TARGET_COLS = ["dmid", "y_class", "y_absmove", "target_available"]


# =============================================================================================
# 1. Feature construction (no target is read here)
# =============================================================================================


def _asof(ts: np.ndarray, vals: np.ndarray, t: np.ndarray, max_age: float = MAX_AGE) -> np.ndarray:
    return hb._asof(ts, vals, np.asarray(t, float), max_age)[0]


def _last_idx(ts: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Index of the last point with stamp + LAG < t (-1 if none)."""
    return np.searchsorted(ts + LAG, t, side="left") - 1


def _cum(x: np.ndarray) -> np.ndarray:
    return np.concatenate([[0.0], np.cumsum(x)])


class Trades:
    """Sorted trades of one market with per-trade derived columns (token-0 sign convention)."""

    def __init__(
        self,
        tr: pd.DataFrame,
        prices: tuple[np.ndarray, np.ndarray],
        first_trade: dict[str, float],
        rec: WalletRecord | None,
        covered_from: float,
    ) -> None:
        tr = tr.sort_values("ts", kind="stable")
        self.ts = tr["ts"].to_numpy(float)
        oi = tr["outcome_index"].to_numpy()
        price = tr["price"].to_numpy(float)
        self.sgn = np.where((tr["side"].to_numpy() == "BUY") == (oi == 0), 1.0, -1.0)
        self.p0 = np.where(oi == 0, price, 1.0 - price)
        self.n = tr["size"].to_numpy(float) * price  # USDC paid for the traded outcome
        self.w = tr["wallet_hash"].astype(str).to_numpy()
        self.codes, self.uniq = pd.factorize(self.w)
        self.covered_from = covered_from
        ts_p, v_p = prices
        ref = _asof(ts_p, v_p, self.ts) if len(ts_p) else np.full(len(self.ts), np.nan)
        self.agg = self.sgn * (self.p0 - ref)
        self.absdev = np.abs(self.p0 - ref)
        ft = np.array([first_trade.get(h, np.nan) for h in self.w], float)
        age = self.ts - ft
        self.fresh = np.isfinite(age) & (age < FRESH_S)
        self.new1d = np.isfinite(age) & (age < NEW1D_S)
        if rec is not None and len(self.ts):
            r, k = rec.lookup(self.w, self.ts)
        else:
            r, k = np.full(len(self.ts), np.nan), np.zeros(len(self.ts))
        self.winner = (k >= REC_MIN_MARKETS) & (r > REC_EDGE)
        self.loser = (k >= REC_MIN_MARKETS) & (r < -REC_EDGE)
        sn = self.sgn * self.n
        p_acq = np.where(self.sgn > 0, self.p0, 1.0 - self.p0)
        convex = (self.n >= CONVEX_USD) & (p_acq <= CONVEX_P)
        self.c = {
            "cnt": _cum(np.ones(len(self.ts))),
            "N": _cum(self.n),
            "S": _cum(sn),
            "L": _cum(np.where(self.n >= LARGE_USD, sn, 0.0)),
            "smS": _cum(np.where(self.n < SMALL_USD, sn, 0.0)),
            "smN": _cum(np.where(self.n < SMALL_USD, self.n, 0.0)),
            "agg": _cum(np.where(self.agg >= AGG_MIN, sn, 0.0)),
            "frS": _cum(np.where(self.fresh, sn, 0.0)),
            "frN": _cum(np.where(self.fresh, self.n, 0.0)),
            "winS": _cum(np.where(self.winner, sn, 0.0)),
            "winN": _cum(np.where(self.winner, self.n, 0.0)),
            "loS": _cum(np.where(self.loser, sn, 0.0)),
            "loN": _cum(np.where(self.loser, self.n, 0.0)),
            "cvx": _cum(np.where(convex, sn, 0.0)),
        }

    def idx(self, t: np.ndarray) -> np.ndarray:
        return np.searchsorted(self.ts, t, side="left")

    def win(self, key: str, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        c = self.c[key]
        return c[self.idx(b)] - c[self.idx(a)]

    def covered(self, a: np.ndarray) -> np.ndarray:
        return a >= self.covered_from


class WalletRecord:
    """Causal per-wallet track record from resolved sample markets: for wallet w and time u, the
    shrunk mean of per-market notional-weighted acquisition edges ``Y_a - q`` over markets whose
    outcome was known (closedTime + 2 days) strictly before u."""

    def __init__(self, entries: pd.DataFrame) -> None:
        e = entries.sort_values(["wallet", "known"], kind="stable")
        self.keys = {}
        for w, g in e.groupby("wallet", sort=False):
            self.keys[w] = (g["known"].to_numpy(float), _cum(g["edge"].to_numpy(float)))

    def lookup(self, wallets: np.ndarray, ts: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        r = np.full(len(ts), np.nan)
        k = np.zeros(len(ts))
        for i, (w, u) in enumerate(zip(wallets, ts, strict=True)):
            v = self.keys.get(w)
            if v is None:
                continue
            j = np.searchsorted(v[0], u, side="left")
            if j:
                k[i] = j
                r[i] = v[1][j] / (j + REC_K)
        return r, k


def build_wallet_record(run_dir: Path, sample: pd.DataFrame) -> WalletRecord:
    """Edges of every wallet in every resolved sampled market (binary payout [1,0] or [0,1])."""
    rows = []
    for r in sample.to_dict("records"):
        if str(r.get("uma_status")) != "resolved" or str(r.get("closed")) not in ("1", "True"):
            continue
        try:
            op = [float(x) for x in json.loads(r["outcome_prices"])]
        except (TypeError, ValueError, KeyError):
            continue
        if sorted(op) != [0.0, 1.0]:
            continue
        close = r.get("close_epoch")
        close = float(close) if close not in (None, "") else float("nan")
        if math.isnan(close):
            end = r.get("end_epoch")
            close = float(end) if end not in (None, "") else float("nan")
        if math.isnan(close):
            continue
        f = run_dir / "trades" / f"{r['market_id']}.csv.gz"
        if not f.exists():
            continue
        tr = pd.read_csv(
            f,
            usecols=["side", "size", "price", "outcome_index", "wallet_hash"],
            dtype={"wallet_hash": str},
        )
        if not len(tr):
            continue
        oi = tr["outcome_index"].to_numpy().astype(int)
        buy = tr["side"].to_numpy() == "BUY"
        a = np.where(buy, oi, 1 - oi)  # outcome acquired
        q = np.where(buy, tr["price"].to_numpy(float), 1.0 - tr["price"].to_numpy(float))
        y = np.where(a == 0, op[0], op[1])
        n = tr["size"].to_numpy(float) * tr["price"].to_numpy(float)
        df = pd.DataFrame({"wallet": tr["wallet_hash"].astype(str), "e": (y - q) * n, "n": n})
        g = df.groupby("wallet").sum()
        g = g[g["n"] > 0]
        rows.append(
            pd.DataFrame({"wallet": g.index, "edge": g["e"] / g["n"], "known": close + REC_DELAY_S})
        )
    ent = (
        pd.concat(rows, ignore_index=True)
        if rows
        else pd.DataFrame(columns=["wallet", "edge", "known"])
    )
    return WalletRecord(ent)


def _rolling_max_abs(d: np.ndarray, lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
    out = np.full(len(lo), np.nan)
    for i, (a, b) in enumerate(zip(lo, hi, strict=True)):
        if b > a:
            out[i] = np.abs(d[a:b]).max()
    return out


def path_features(
    t: np.ndarray, ts: np.ndarray, v: np.ndarray, N24: np.ndarray, N7d: np.ndarray
) -> dict[str, np.ndarray]:
    """10-minute price-path features (points with stamp + LAG < t)."""
    n = len(t)
    out = {
        k: np.full(n, np.nan)
        for k in (
            "f_jump_ratio",
            "f_vol_of_vol",
            "f_vol_ratio",
            "f_hours_since_move",
            "f_semivar_asym",
            "f_illiq_surprise",
            "f_chg_6h",
        )
    }
    if len(ts) < 3:
        return out
    d = np.diff(v)
    c2, ca = _cum(d**2), _cum(np.abs(d))
    cp, cm = _cum(np.where(d > 0, d**2, 0.0)), _cum(np.where(d < 0, d**2, 0.0))
    u = _last_idx(ts, t)

    def lo_of(w: float, tt: np.ndarray = t) -> np.ndarray:
        return np.searchsorted(ts, tt - LAG - w, side="left")

    def rv(w: float, tt: np.ndarray) -> np.ndarray:
        uu = _last_idx(ts, tt)
        s = lo_of(w, tt)
        nd = uu - s
        with np.errstate(invalid="ignore", divide="ignore"):
            return np.where(
                nd >= 3,
                np.sqrt(
                    (c2[np.maximum(uu, 0)] - c2[np.minimum(s, np.maximum(uu, 0))])
                    / np.maximum(nd, 1)
                ),
                np.nan,
            )

    rv7 = rv(7 * DAY, t)
    s6 = lo_of(6 * H)
    out["f_jump_ratio"] = np.where(
        u - s6 >= 1, _rolling_max_abs(d, s6, np.maximum(u, 0)) / (rv7 + 1e-4), np.nan
    )
    rvs = np.column_stack([rv(2 * H, t - 2 * H * k) for k in range(12)])
    with np.errstate(invalid="ignore", divide="ignore"):
        okc = np.isfinite(rvs).sum(1)
        mu = np.nanmean(np.where(np.isfinite(rvs), rvs, np.nan), axis=1)
        sd = np.nanstd(np.where(np.isfinite(rvs), rvs, np.nan), axis=1)
        out["f_vol_of_vol"] = np.where((okc >= 6) & (mu > 0), sd / mu, np.nan)
        out["f_vol_ratio"] = rv(2 * H, t) / (rv7 + 1e-4)
    big = np.flatnonzero(np.abs(d) >= MOVE_BIG)  # diff j: between points j and j+1
    if len(big):
        j = np.searchsorted(big, u, side="left") - 1  # last big diff with j < u (point j+1 <= u)
        last_t = np.where(j >= 0, ts[np.minimum(big[np.maximum(j, 0)] + 1, len(ts) - 1)], np.nan)
        hrs = (t - last_t) / H
        out["f_hours_since_move"] = np.where(np.isfinite(hrs), np.minimum(hrs, 168.0), 168.0)
    else:
        out["f_hours_since_move"] = np.full(n, 168.0)
    out["f_hours_since_move"] = np.where(u >= 1, out["f_hours_since_move"], np.nan)
    s24 = lo_of(DAY)
    uu = np.maximum(u, 0)
    tot = c2[uu] - c2[np.minimum(s24, uu)]
    with np.errstate(invalid="ignore", divide="ignore"):
        out["f_semivar_asym"] = np.where(
            (u - s24 >= 3) & (tot > 0),
            ((cp[uu] - cp[np.minimum(s24, uu)]) - (cm[uu] - cm[np.minimum(s24, uu)])) / tot,
            np.nan,
        )
        s7 = lo_of(7 * DAY)
        il24 = (ca[uu] - ca[np.minimum(s24, uu)]) / (N24 + 100.0)
        il7 = (ca[uu] - ca[np.minimum(s7, uu)]) / (N7d + 700.0)
        out["f_illiq_surprise"] = np.where(
            (u - s24 >= 3) & np.isfinite(N24) & np.isfinite(N7d),
            np.log((il24 + 1e-6) / (il7 + 1e-6)),
            np.nan,
        )
    m6 = _asof(ts, v, t - 6 * H)
    m0 = _asof(ts, v, t)
    out["f_chg_6h"] = m0 - m6
    return out


def flow_features(
    t: np.ndarray, s: np.ndarray, mid: np.ndarray, T: Trades | None, shift_s: float = 0.0
) -> dict[str, np.ndarray]:
    """Trade features on price-aligned windows ending at ``s - shift_s`` (``s`` = stamp of the last
    usable price point). Windows not fully covered by a truncated trade history are NaN."""
    n = len(t)
    names = (
        "f_n_1h",
        "f_n_2h",
        "f_n_6h",
        "f_n_24h",
        "f_N_24h",
        "f_N_7d",
        "f_imb_1h",
        "f_imb_2h",
        "f_imb_6h",
        "f_imb_24h",
        "f_imb_7d",
        "f_large_flow_6h",
        "f_small_imb_6h",
        "f_n_small_6h",
        "f_agg_flow_6h",
        "f_persist_6h",
        "f_flow_surprise",
        "f_burst_2h",
        "f_last_trade_age_h",
        "f_spread_proxy",
        "f_fresh_flow_24h",
        "f_n_fresh_24h",
        "f_win_flow_24h",
        "f_n_win_24h",
        "f_lose_flow_24h",
        "f_n_lose_24h",
        "f_top1_dir",
        "f_top1_share",
        "f_hhi_24h",
        "f_n_wallets_24h",
        "f_large_rel_2h",
        "f_quiet",
        "f_convex_dir",
        "f_n_new1d_24h",
    )
    out = {k: np.full(n, np.nan) for k in names}
    if T is None or not len(T.ts):
        for k in (
            "f_n_1h",
            "f_n_2h",
            "f_n_6h",
            "f_n_24h",
            "f_N_24h",
            "f_N_7d",
            "f_n_small_6h",
            "f_n_fresh_24h",
            "f_n_win_24h",
            "f_n_lose_24h",
            "f_n_wallets_24h",
            "f_n_new1d_24h",
        ):
            out[k] = np.zeros(n)
        if T is not None:
            for k in (
                "f_large_flow_6h",
                "f_fresh_flow_24h",
                "f_win_flow_24h",
                "f_lose_flow_24h",
                "f_convex_dir",
            ):
                out[k] = np.zeros(n)
        return out
    e = np.where(np.isfinite(s), s - shift_s, t - LAG - shift_s)

    def cov(w: float) -> np.ndarray:
        return T.covered(e - w)

    def nn(w: float, key: str = "cnt") -> np.ndarray:
        return np.where(cov(w), T.win(key, e - w, e), np.nan)

    for w, tag in ((H, "1h"), (2 * H, "2h"), (6 * H, "6h"), (DAY, "24h"), (7 * DAY, "7d")):
        cnt, N, S = nn(w), nn(w, "N"), nn(w, "S")
        if tag != "7d":
            out[f"f_n_{tag}"] = cnt
        with np.errstate(invalid="ignore", divide="ignore"):
            out[f"f_imb_{tag}"] = np.where(N > 0, S / N, np.nan)
        if tag == "24h":
            out["f_N_24h"] = N
        if tag == "7d":
            out["f_N_7d"] = N
    N6 = nn(6 * H, "N")
    with np.errstate(invalid="ignore", divide="ignore"):
        out["f_large_flow_6h"] = np.where(
            np.isfinite(out["f_N_7d"]),
            nn(6 * H, "L") / np.maximum(out["f_N_7d"] / 7.0, 100.0),
            np.nan,
        )
        smN = nn(6 * H, "smN")
        out["f_small_imb_6h"] = np.where(smN > 0, nn(6 * H, "smS") / smN, np.nan)
        out["f_n_small_6h"] = np.where(cov(6 * H), np.where(smN > 0, 1.0, 0.0), np.nan)
        out["f_agg_flow_6h"] = np.where(N6 > 0, nn(6 * H, "agg") / N6, np.nan)
        signs = []
        for k in range(3):
            a, b = e - 2 * H * (k + 1), e - 2 * H * k
            Nk = np.where(T.covered(a), T.win("N", a, b), np.nan)
            Sk = np.where(T.covered(a), T.win("S", a, b), np.nan)
            signs.append(np.where(Nk > 0, np.sign(Sk), np.nan))
        sg = np.column_stack(signs)
        allsame = np.all(np.isfinite(sg), axis=1) & (np.abs(sg.sum(1)) == 3)
        out["f_persist_6h"] = np.where(
            np.all(np.isfinite(sg), axis=1), np.where(allsame, sg[:, 0], 0.0), np.nan
        )
        out["f_flow_surprise"] = out["f_imb_24h"] - out["f_imb_7d"]
        n24 = out["f_n_24h"]
        out["f_burst_2h"] = np.where(n24 > 0, out["f_n_2h"] / (n24 / 12.0), np.nan)
        N24 = out["f_N_24h"]
        out["f_fresh_flow_24h"] = np.where(
            N24 > 0, nn(DAY, "frS") / N24, np.where(N24 == 0, 0, np.nan)
        )
        out["f_n_fresh_24h"] = np.where(cov(DAY), (nn(DAY, "frN") > 0).astype(float), np.nan)
        out["f_win_flow_24h"] = np.where(
            N24 > 0, nn(DAY, "winS") / N24, np.where(N24 == 0, 0, np.nan)
        )
        out["f_n_win_24h"] = np.where(cov(DAY), (nn(DAY, "winN") > 0).astype(float), np.nan)
        out["f_lose_flow_24h"] = np.where(
            N24 > 0, nn(DAY, "loS") / N24, np.where(N24 == 0, 0, np.nan)
        )
        out["f_n_lose_24h"] = np.where(cov(DAY), (nn(DAY, "loN") > 0).astype(float), np.nan)
        cv = nn(DAY, "cvx")
        out["f_convex_dir"] = np.where(np.isfinite(cv), np.sign(cv), np.nan)
    # last trade age, spread proxy, wallet concentration, max trade: per-origin slices
    hi = T.idx(e)
    lo24 = T.idx(e - DAY)
    lo2 = T.idx(e - 2 * H)
    last = hi - 1
    out["f_last_trade_age_h"] = np.where(last >= 0, (t - T.ts[np.maximum(last, 0)]) / H, np.nan)
    ok24 = cov(DAY)
    ok2 = cov(2 * H)
    for i in range(n):
        a, b = lo24[i], hi[i]
        if not ok24[i]:
            continue
        if b <= a:
            out["f_n_wallets_24h"][i] = 0.0
            out["f_n_new1d_24h"][i] = 0.0
            continue
        dev = T.absdev[a:b]
        dev = dev[np.isfinite(dev)]
        if len(dev):
            out["f_spread_proxy"][i] = float(np.median(dev))
        cw = T.codes[a:b]
        nw = T.n[a:b]
        vol = np.bincount(cw, weights=nw)
        tot = vol.sum()
        out["f_n_wallets_24h"][i] = float((vol > 0).sum())
        out["f_n_new1d_24h"][i] = float(len(np.unique(cw[T.new1d[a:b]])))
        if tot > 0 and (vol > 0).sum() >= 2:
            j = int(np.argmax(vol))
            sh = vol / tot
            out["f_top1_share"][i] = float(sh[j])
            out["f_hhi_24h"][i] = float((sh**2).sum())
            net = float((T.sgn[a:b] * nw)[cw == j].sum())
            out["f_top1_dir"][i] = float(sh[j] * np.sign(net))
        elif tot > 0:
            out["f_top1_share"][i] = 1.0
            out["f_hhi_24h"][i] = 1.0
            net = float((T.sgn[a:b] * nw).sum())
            out["f_top1_dir"][i] = float(np.sign(net))
        a2 = lo2[i]
        if ok2[i] and b > a2:
            mean24 = tot / max(b - a, 1)
            if mean24 > 0:
                out["f_large_rel_2h"][i] = float(T.n[a2:b].max() / mean24)
    # quiet: 24h notional below the market's own median daily notional over the prior 29 days;
    # a day counts only if covered by the fetched history and not before the market's first trade
    first_trade = T.ts[0]
    daily = np.column_stack(
        [
            np.where(
                T.covered(e - DAY * (k + 1)) & (e - DAY * (k + 1) >= first_trade),
                T.win("N", e - DAY * (k + 1), e - DAY * k),
                np.nan,
            )
            for k in range(1, 30)
        ]
    )
    okd = np.isfinite(daily).sum(1) >= 7
    med = np.full(len(t), np.nan)
    if okd.any():
        med[okd] = np.nanmedian(daily[okd], axis=1)
    out["f_quiet"] = np.where(
        okd & np.isfinite(out["f_N_24h"]), (out["f_N_24h"] < med).astype(float), np.nan
    )
    return out


class Siblings:
    """Neg-risk sums, sibling lead-lag and deadline-ladder features from fetched sibling series."""

    def __init__(self, events: dict[str, dict], meta: pd.DataFrame, run_dir: Path, sib_dir: Path):
        self.events, self.run_dir, self.sib_dir = events, run_dir, sib_dir
        self.meta = meta.set_index("market_id")
        self.cache: dict[str, tuple[np.ndarray, np.ndarray] | None] = {}

    def series(self, market_id: str):
        if market_id in self.cache:
            return self.cache[market_id]
        out = None
        for p in (
            self.run_dir / "prices" / f"{market_id}.csv.gz",
            self.sib_dir / f"{market_id}.csv.gz",
        ):
            if p.exists():
                df = pd.read_csv(p)
                if len(df):
                    out = (df["t"].to_numpy(float), df["p"].to_numpy(float))
                break
        if len(self.cache) > 4000:
            self.cache.clear()
        self.cache[market_id] = out
        return out

    def features(self, market_id: str, t: np.ndarray, mid: np.ndarray) -> dict[str, np.ndarray]:
        n = len(t)
        out = {
            k: np.full(n, np.nan)
            for k in (
                "f_nr_dev",
                "f_nr_absdev",
                "f_sib_nr_d2h",
                "f_sib_nr_d24h",
                "f_sib_d2h",
                "f_sib_d24h",
                "f_ladder_z",
                "f_ladder_viol",
            )
        }
        if market_id not in self.meta.index:
            return out
        r = self.meta.loc[market_id]
        ev = self.events.get(str(r["event_id"]))
        if ev is None:
            return out
        others = [m for m in ev["markets"] if m["market_id"] != market_id]
        if ev["neg_risk"]:
            self._negrisk(ev, market_id, others, t, mid, out)
        else:
            self._comove(others, t, out)
        if isinstance(r["ladder_id"], str) and r["ladder_id"]:
            self._ladder(ev, r, t, mid, out)
        return out

    @staticmethod
    def _alive(m: dict, t: np.ndarray) -> np.ndarray:
        c0 = m["created_epoch"] if not math.isnan(m["created_epoch"]) else m["start_epoch"]
        a = np.ones(len(t), bool) if math.isnan(c0) else t >= c0
        if not math.isnan(m["close_epoch"]):
            a &= t < m["close_epoch"]
        return a

    def _negrisk(self, ev, market_id, others, t, mid, out) -> None:
        full = (2 <= ev["n_markets"] <= bd.NR_MAX_MEMBERS) and not ev["neg_risk_augmented"]
        S = mid.copy()
        complete = np.ones(len(t), bool)
        d2 = np.zeros(len(t))
        d24 = np.zeros(len(t))
        k2 = np.zeros(len(t))
        k24 = np.zeros(len(t))
        for m in others:
            alive = self._alive(m, t)
            se = self.series(m["market_id"])
            if se is None:
                complete &= ~alive
                continue
            p = _asof(se[0], se[1], t, NR_SUM_MAX_AGE)
            complete &= ~alive | np.isfinite(p)
            S = S + np.where(alive & np.isfinite(p), p, 0.0)
            for lag, acc, kk in ((2 * H, d2, k2), (DAY, d24, k24)):
                q = _asof(se[0], se[1], t - lag, NR_SUM_MAX_AGE)
                okm = alive & np.isfinite(p) & np.isfinite(q)
                acc += np.where(okm, p - q, 0.0)
                kk += okm
        if full:
            ok = complete & (S > 0)
            out["f_nr_dev"] = np.where(ok, -(S - 1.0) * mid / np.where(ok, S, 1.0), np.nan)
            out["f_nr_absdev"] = np.where(ok, np.abs(S - 1.0), np.nan)
        out["f_sib_nr_d2h"] = np.where(k2 > 0, d2, np.nan)
        out["f_sib_nr_d24h"] = np.where(k24 > 0, d24, np.nan)

    def _comove(self, others, t, out) -> None:
        d2 = np.zeros(len(t))
        d24 = np.zeros(len(t))
        k2 = np.zeros(len(t))
        k24 = np.zeros(len(t))
        for m in others:
            se = self.series(m["market_id"])
            if se is None:
                continue
            alive = self._alive(m, t)
            p = _asof(se[0], se[1], t)
            for lag, acc, kk in ((2 * H, d2, k2), (DAY, d24, k24)):
                q = _asof(se[0], se[1], t - lag)
                okm = alive & np.isfinite(p) & np.isfinite(q)
                acc += np.where(okm, p - q, 0.0)
                kk += okm
        with np.errstate(invalid="ignore", divide="ignore"):
            out["f_sib_d2h"] = np.where(k2 > 0, d2 / k2, np.nan)
            out["f_sib_d24h"] = np.where(k24 > 0, d24 / k24, np.nan)

    def _ladder(self, ev, r, t, mid, out) -> None:
        li = int(str(r["ladder_id"]).split(":")[1])
        lads = bd.event_ladders(ev)
        if li >= len(lads):
            return
        lad = lads[li]
        ids = [x["market_id"] for x in lad]
        j = ids.index(r.name) if r.name in ids else -1
        if j < 0 or j + 1 >= len(lad):
            return
        near, far = lad[j], lad[j + 1]
        se_far = self.series(far["market_id"])
        se_near = self.series(near["market_id"])
        if se_far is None or se_near is None:
            return
        d1, d2 = near["deadline"], far["deadline"]
        vf = _asof(se_far[0], se_far[1], t)
        out["f_ladder_viol"] = np.where(
            np.isfinite(vf) & self._alive(far, t), np.maximum(0.0, mid - vf), np.nan
        )
        steps = np.arange(0, LADDER_Z_STEPS + 1)
        R = np.full((len(t), len(steps)), np.nan)
        for c, k in enumerate(steps):
            tt = t - 6 * H * k
            R[:, c] = self._ladder_R(se_near, se_far, tt, d1, d2)
        hist = R[:, 1:]
        cnt = np.isfinite(hist).sum(1)
        with np.errstate(invalid="ignore", divide="ignore"):
            sd = np.nanstd(np.where(np.isfinite(hist), hist, np.nan), axis=1, ddof=1)
            z = R[:, 0] / sd
        left_ok = (d1 - t) >= LADDER_MIN_LEFT_S
        out["f_ladder_z"] = np.where(left_ok & (cnt >= LADDER_Z_MIN) & (sd > 0), z, np.nan)

    @staticmethod
    def _ladder_R(se_near, se_far, tt, d1, d2) -> np.ndarray:
        u = tt - 6 * H
        vn1, vf1 = _asof(se_near[0], se_near[1], tt), _asof(se_far[0], se_far[1], tt)
        vn0, vf0 = _asof(se_near[0], se_near[1], u), _asof(se_far[0], se_far[1], u)
        with np.errstate(invalid="ignore", divide="ignore"):
            h = -np.log(np.clip(1.0 - vf0, 1e-6, 1.0)) / np.maximum(d2 - u, H)

            def nc(x):
                a = 1.0 - np.exp(-h * np.maximum(d1 - x, 0.0))
                b = 1.0 - np.exp(-h * np.maximum(d2 - x, 0.0))
                return np.where(b > 1e-9, a / b, np.nan)

            N1 = np.where(vf1 > 0.005, vn1 / vf1, np.nan)
            N0 = np.where(vf0 > 0.005, vn0 / vf0, np.nan)
            R = (N1 - N0) - (nc(tt) - nc(u))
        ok = (vf0 > 0.02) & (vf0 < 0.97) & (d1 - tt > 0)
        return np.where(ok, R, np.nan)


def _band_spread(p: np.ndarray) -> np.ndarray:
    out = np.full(len(p), np.nan)
    lo = 0.0
    for hi, sp in BAND_SPREAD:
        out = np.where((p >= lo) & (p < hi), sp, out)
        lo = hi
    return out


def _read_panel(path: Path, cols: list[str], markets: set[str] | None) -> pd.DataFrame:
    parts = []
    for ch in pd.read_csv(
        path, usecols=cols, dtype={"market_id": str, "event_id": str}, chunksize=200_000
    ):
        parts.append(ch if markets is None else ch[ch["market_id"].isin(markets)])
    return pd.concat(parts, ignore_index=True)


def load_base(
    run_dir: Path, markets: set[str] | None = None, extra_cols: tuple[str, ...] = ()
) -> pd.DataFrame:
    """2h panel (features + 2h target) joined with the 6h and 24h targets. ``extra_cols``: further
    panel columns to carry (e.g. ``sample_weight`` in weighted runs such as h3_power)."""
    base = _read_panel(
        run_dir / "panel_H2h.csv.gz", PANEL_COLS + list(extra_cols) + TARGET_COLS, markets
    )
    base = base.rename(
        columns={"dmid": "d_2", "y_class": "y3_2", "y_absmove": "ya_2", "target_available": "ok_2"}
    )
    for h in (6, 24):
        p = _read_panel(
            run_dir / f"panel_H{h}h.csv.gz", ["market_id", "t_i", *TARGET_COLS], markets
        )
        p = p.rename(
            columns={
                "dmid": f"d_{h}",
                "y_class": f"y3_{h}",
                "y_absmove": f"ya_{h}",
                "target_available": f"ok_{h}",
            }
        )
        base = base.merge(p, on=["market_id", "t_i"], how="left")
    for h in (2, 6, 24):
        base[f"ok_{h}"] = base[f"ok_{h}"].fillna(False).astype(bool)
    return base


def add_new_wallets(df: pd.DataFrame, run_dir: Path) -> pd.DataFrame:
    """``nw_share_new7d`` from ``history_sources.new_wallet_features`` (true first trades)."""
    p = (
        run_dir.parents[1]
        / "history_sources"
        / "new_wallets"
        / f"new_wallet_features_{run_dir.name}.csv.gz"
    )
    w = pd.read_csv(
        p, usecols=["market_id", "origin_ts", "nw_share_new7d"], dtype={"market_id": str}
    )
    w["origin_ts"] = w["origin_ts"].astype(float)
    w = w.drop_duplicates(["market_id", "origin_ts"])
    return df.merge(
        w, left_on=["market_id", "t_i"], right_on=["market_id", "origin_ts"], how="left"
    ).drop(columns=["origin_ts"])


def build_features(
    run_dir: Path,
    out_dir: Path,
    log=print,
    shift_s: float = 0.0,
    markets: set[str] | None = None,
    first_trade_path: Path | None = None,
    extra_cols: tuple[str, ...] = (),
) -> pd.DataFrame:
    """Every battery feature for every panel origin (targets are carried through untouched).
    ``first_trade_path``: wallet first-trade map (default: the h2-era ``history_sources`` map)."""
    base = load_base(run_dir, markets, extra_cols)
    sample = pd.read_csv(run_dir / "sample.csv.gz", dtype=str, keep_default_na=False)
    meta = pd.read_csv(
        out_dir / "market_meta.csv.gz", dtype={"market_id": str, "event_id": str, "ladder_id": str}
    )
    meta["ladder_id"] = meta["ladder_id"].fillna("")
    events = {e["event_id"]: e for e in bd.load_jsonl_gz(out_dir / "events_meta.jsonl.gz")}
    sib = Siblings(events, meta, run_dir, out_dir / "siblings")
    prog = {}
    for line in (run_dir / "progress.jsonl").read_text().splitlines():
        if line.strip():
            d = json.loads(line)
            prog[str(d["market_id"])] = d
    ft = {}
    ftp = first_trade_path or (
        run_dir.parents[1] / "history_sources" / "new_wallets" / "first_trade.jsonl"
    )
    for line in ftp.read_text().splitlines():
        if line.strip():
            d = json.loads(line)
            if d.get("first_trade_ts") is not None:
                ft[d["wallet_hash"]] = float(d["first_trade_ts"])
    log(f"wallet record: building from resolved sample markets; first-trade map {len(ft)}")
    rec = build_wallet_record(run_dir, sample)
    log(f"wallet record: {len(rec.keys)} wallets with >= 1 resolved market")
    parts = []
    t0 = time.time()
    for i, (mid, g) in enumerate(base.groupby("market_id", sort=True)):
        g = g.sort_values("t_i")
        t = g["t_i"].to_numpy(float)
        m = g["mid_i"].to_numpy(float)
        pf = run_dir / "prices" / f"{mid}.csv.gz"
        ts, v = hb.load_prices(pf) if pf.exists() else (np.array([]), np.array([]))
        u = _last_idx(ts, t) if len(ts) else np.full(len(t), -1)
        s_last = np.where(u >= 0, ts[np.maximum(u, 0)] if len(ts) else np.nan, np.nan)
        tf = run_dir / "trades" / f"{mid}.csv.gz"
        T = None
        if tf.exists():
            tr = hb.load_trades(tf)
            p = prog.get(mid, {})
            cov_from = (
                float(p.get("trades_oldest_ts"))
                if p.get("trades_truncated") and p.get("trades_oldest_ts") is not None
                else -np.inf
            )
            T = (
                Trades(tr, (ts, v), ft, rec, cov_from)
                if len(tr)
                else Trades(tr, (ts, v), ft, None, cov_from)
            )
        fl = flow_features(t, s_last, m, T, shift_s)
        pa = path_features(t, ts, v, fl["f_N_24h"], fl["f_N_7d"])
        sf = sib.features(mid, t, m)
        df = pd.DataFrame({"market_id": mid, "t_i": t, **fl, **pa, **sf})
        parts.append(df)
        if i % 200 == 0:
            log(f"features: market {i} ({time.time() - t0:.0f}s)")
    feats = pd.concat(parts, ignore_index=True)
    df = base.merge(feats, on=["market_id", "t_i"], how="left")
    df = df.merge(
        meta[
            [
                "market_id",
                "asym_class",
                "topic",
                "event_neg_risk",
                "event_n_markets",
                "neg_risk_augmented",
                "ladder_id",
            ]
        ],
        on="market_id",
        how="left",
    )
    smp = sample[
        ["market_id", "uma_status", "outcome_prices", "closed", "close_epoch", "end_epoch"]
    ].copy()
    df = df.merge(smp, on="market_id", how="left")
    df = add_book(df, run_dir)
    df = add_new_wallets(df, run_dir)
    df = derive(df)
    return df


def add_book(df: pd.DataFrame, run_dir: Path) -> pd.DataFrame:
    p = run_dir.parents[1] / "history_sources" / "book_features" / "book_features.csv.gz"
    b = pd.read_csv(p, dtype={"market_id": str, "token_id": str, "condition_id": str})
    b = b[b["state"] == "two_sided"].copy()
    b["origin_ts"] = b["origin_ts"].astype(float)
    keep = [
        "sw_best_bid",
        "sw_best_ask",
        "sw_depth_bid_5c",
        "sw_depth_ask_5c",
        "ml_sw_spread",
        "ml_sw_imb_1c",
        "ml_sw_microprice_disp",
    ]
    b = b.drop_duplicates(["market_id", "origin_ts"])[["market_id", "origin_ts", *keep]]
    cur = b.rename(columns={c: f"bk_{c}" for c in keep})
    prev = b.rename(columns={c: f"bp_{c}" for c in keep})
    prev["origin_ts"] = prev["origin_ts"] + 6 * H
    df = df.merge(
        cur, left_on=["market_id", "t_i"], right_on=["market_id", "origin_ts"], how="left"
    ).drop(columns=["origin_ts"])
    df = df.merge(
        prev, left_on=["market_id", "t_i"], right_on=["market_id", "origin_ts"], how="left"
    ).drop(columns=["origin_ts"])
    return df


def derive(df: pd.DataFrame) -> pd.DataFrame:
    """Derived columns, controls, regime indicators, clusters and the split."""
    d = df
    d["event_c"] = np.where(
        d["event_id"].fillna("").astype(str).ne(""),
        "e:" + d["event_id"].fillna("").astype(str),
        "m:" + d["market_id"],
    )
    d["day_c"] = (d["t_i"] // DAY).astype(int).astype(str)
    d["month"] = pd.to_datetime(d["t_i"], unit="s", utc=True).dt.strftime("%Y-%m")
    d["traded"] = d["traded_before_t"].ne(0)
    d["split"] = np.where(
        d["t_i"] + EMBARGO_S <= SPLIT_TS,
        "disc",
        np.where(d["t_i"] >= SPLIT_TS + EMBARGO_S, "judge", "embargo"),
    )
    for c, src in (
        ("c_chg_1h", "ml_chg_1h"),
        ("c_chg_1d", "ml_chg_1d"),
        ("c_chg_1w", "ml_chg_1w"),
        ("c_dprev", "ml_own_dmid_prev"),
    ):
        d[c] = d[src].fillna(0.0)
    d["c_dprev_missing"] = d["ml_own_dmid_prev"].isna().astype(float)
    m = d["mid_i"]
    d["f_log_age"] = np.log1p(d["ml_market_age_h"])
    d["f_log_last_trade_age"] = np.log1p(d["f_last_trade_age_h"].clip(upper=720))
    d["f_vol_surprise"] = np.log1p(d["f_N_24h"]) - np.log1p(d["f_N_7d"] / 7.0)
    d["f_vol_confirm"] = np.sign(d["c_chg_1d"]) * d["f_vol_surprise"]
    # microstructure interactions (moderators; discovery-median cut is fixed in fit_cuts)
    d["f_no_trade_2h"] = (d["f_n_2h"] == 0).astype(float).where(d["f_n_2h"].notna())
    d["f_rev_notrade"] = d["c_dprev"] * d["f_no_trade_2h"]
    d["f_extreme"] = (d["ml_dist_01"] < 0.10).astype(float)
    d["f_rev_extreme"] = d["c_dprev"] * d["f_extreme"]
    d["f_confirm"] = (
        (np.sign(d["f_imb_2h"]) == np.sign(d["c_dprev"])) & (d["f_n_2h"] >= 1) & (d["c_dprev"] != 0)
    ).astype(float)
    d["f_rev_confirm"] = d["c_dprev"] * d["f_confirm"]
    hrs = pd.to_datetime(d["t_i"], unit="s", utc=True)
    d["hour"] = hrs.dt.hour
    d["weekday"] = hrs.dt.weekday
    d["f_hour_sin"] = np.sin(2 * np.pi * d["hour"] / 24.0)
    d["f_hour_cos"] = np.cos(2 * np.pi * d["hour"] / 24.0)
    for k in range(7):
        d[f"f_wd_{k}"] = (d["weekday"] == k).astype(float)
    d["f_weekend"] = (d["weekday"] >= 5).astype(float)
    d["f_rev_weekend"] = d["c_dprev"] * d["f_weekend"]
    tte_h = np.expm1(d["ml_log_hours_to_end"])
    d["f_near_end"] = ((tte_h <= 72) & (tte_h > 0)).astype(float).where(tte_h.notna())
    d["f_mid_c"] = m - 0.5
    d["f_longshot"] = (m <= 0.15).astype(float)
    d["f_favourite"] = (m >= 0.85).astype(float)
    cats = [
        "sports",
        "crypto",
        "politics",
        "unknown",
        "economics",
        "culture",
        "finance",
        "tech",
        "weather",
        "mentions",
        "other",
    ]
    fc = d["fee_category"].fillna("unknown").astype(str).str.split(":").str[0]
    for c in cats:
        d[f"f_cat_{c}"] = (fc == c).astype(float)
    d["fee_cat"] = fc
    d["f_asym"] = (d["asym_class"] == "asymmetric").astype(float)
    for c in ("asymmetric", "public", "other"):
        d[f"f_cls_{c}"] = (d["asym_class"] == c).astype(float)
    d["f_rev_asym"] = d["c_dprev"] * d["f_asym"]
    d["f_flow_asym"] = d["f_imb_6h"] * d["f_asym"]
    d["f_asym_longshot"] = d["f_asym"] * (m <= 0.20).astype(float)
    d["f_low20"] = (m <= 0.20).astype(float)
    d["f_mom_extreme"] = d["c_chg_1d"] * d["f_extreme"]
    d["f_flow_longshot"] = d["f_imb_24h"] * d["f_low20"]
    d["f_extreme20"] = ((m <= 0.20) | (m >= 0.80)).astype(float)
    # book (pmxt) derived
    tot = d["bk_sw_depth_bid_5c"] + d["bk_sw_depth_ask_5c"]
    totp = d["bp_sw_depth_bid_5c"] + d["bp_sw_depth_ask_5c"]
    d["f_bk_log_depth"] = np.log1p(tot)
    d["f_bk_depth_chg"] = np.log1p(tot) - np.log1p(totp)
    d["f_bk_side_withdraw"] = (
        np.log1p(d["bk_sw_depth_bid_5c"]) - np.log1p(d["bp_sw_depth_bid_5c"])
    ) - (np.log1p(d["bk_sw_depth_ask_5c"]) - np.log1p(d["bp_sw_depth_ask_5c"]))
    d["f_bk_spread_chg"] = d["bk_ml_sw_spread"] - d["bp_ml_sw_spread"]
    d["has_book"] = d["bk_sw_best_bid"].notna() & d["bk_sw_best_ask"].notna()
    d["has_book_prev"] = d["has_book"] & d["bp_sw_best_bid"].notna() & d["bp_sw_best_ask"].notna()
    # theory interactions
    p_acq = np.where(d["f_imb_2h"] > 0, m, 1 - m)
    d["f_convex_pressure"] = d["f_imb_2h"] * np.log1p(d["f_large_rel_2h"]) * d["f_top1_share"]
    d["pop_convex"] = (d["f_n_2h"] >= 3) & (p_acq <= 0.20)
    resp = np.sign(d["f_imb_2h"]) * d["c_dprev"]
    d["f_no_response"] = (resp <= 0).astype(float)
    d["f_pressure_noresp"] = d["f_imb_2h"] * d["f_top1_share"] * d["f_no_response"]
    d["f_flow_quiet"] = d["f_imb_6h"] * d["f_quiet"]
    d["f_flow_near_end"] = d["f_imb_6h"] * d["f_near_end"]
    d["f_fresh_asym"] = d["f_fresh_flow_24h"] * d["f_asym"]
    # resolution excess (outcome-0 payout minus mid) for resolved binary markets
    y0 = d["outcome_prices"].map(_payout0)
    d["res_excess"] = np.where(d["uma_status"].eq("resolved") & y0.notna(), y0 - m, np.nan)
    d["ok_res"] = np.isfinite(d["res_excess"])
    return d


def _payout0(raw) -> float:
    try:
        op = [float(x) for x in json.loads(raw)]
    except (TypeError, ValueError):
        return np.nan
    return op[0] if sorted(op) == [0.0, 1.0] else np.nan


def fit_cuts(d: pd.DataFrame) -> dict:
    """Discovery-only quantities used by declared features (moderator medians, z-scales)."""
    disc = d[(d["split"] == "disc") & d["traded"]]
    cuts = {
        "illiq_median_N24": float(disc["f_N_24h"].median()),
        "lrv1d_mean": float(np.log(disc["ml_rv_1d"] + 1e-4).mean()),
        "lrv1d_sd": float(np.log(disc["ml_rv_1d"] + 1e-4).std()),
        "lte_mean": float(disc["ml_log_hours_to_end"].mean()),
        "lte_sd": float(disc["ml_log_hours_to_end"].std()),
    }
    return cuts


def apply_cuts(d: pd.DataFrame, cuts: dict) -> pd.DataFrame:
    d["f_illiq"] = (
        (d["f_N_24h"] < cuts["illiq_median_N24"]).astype(float).where(d["f_N_24h"].notna())
    )
    d["f_rev_illiq"] = d["c_dprev"] * d["f_illiq"]
    d["f_z_lrv1d"] = (np.log(d["ml_rv_1d"] + 1e-4) - cuts["lrv1d_mean"]) / cuts["lrv1d_sd"]
    d["f_rev_vol"] = d["c_dprev"] * d["f_z_lrv1d"]
    d["f_z_lte"] = (d["ml_log_hours_to_end"] - cuts["lte_mean"]) / cuts["lte_sd"]
    d["f_rev_tte"] = d["c_dprev"] * d["f_z_lte"]
    return d


# =============================================================================================
# 2. Statistics
# =============================================================================================


def _resid(y: np.ndarray, Z: np.ndarray) -> np.ndarray:
    coef, *_ = np.linalg.lstsq(Z, y, rcond=None)
    return y - Z @ coef


def _cr_var_of_sum(scores: np.ndarray, cl: np.ndarray) -> float:
    codes, uniq = pd.factorize(cl)
    g = len(uniq)
    s = np.bincount(codes, weights=scores, minlength=g)
    return float((s**2).sum() * g / max(g - 1, 1))


def _twoway(scores: np.ndarray, a: np.ndarray, b: np.ndarray) -> tuple[float, float, float]:
    va = _cr_var_of_sum(scores, a)
    vb = _cr_var_of_sum(scores, b)
    vab = _cr_var_of_sum(scores, np.char.add(np.char.add(a.astype(str), "|"), b.astype(str)))
    v2 = va + vb - vab
    return va, vb, (v2 if v2 > 0 else max(va, vb))


def beta_test(
    y: np.ndarray,
    x: np.ndarray,
    Z: np.ndarray,
    ev: np.ndarray,
    day: np.ndarray,
    sign: int | None,
    n_boot: int = N_BOOT,
    seed: int = SEED,
    w: np.ndarray | None = None,
) -> dict:
    """OLS slope of ``x`` given ``Z`` (with intercept), CR SEs (event; two-way event x day).
    ``sign`` = direction to test one-sided (None: report two-sided only). ``w``: optional row
    weights (WLS: weighted partialling, weighted scores); None gives the unweighted estimator."""
    Z1 = np.column_stack([np.ones(len(y)), Z]) if Z.size else np.ones((len(y), 1))
    wt = np.ones(len(y)) if w is None else np.asarray(w, float)
    if w is None:
        xt = _resid(x, Z1)
        yt = _resid(y, Z1)
    else:
        sw = np.sqrt(wt)
        cx, *_ = np.linalg.lstsq(Z1 * sw[:, None], x * sw, rcond=None)
        cy, *_ = np.linalg.lstsq(Z1 * sw[:, None], y * sw, rcond=None)
        xt, yt = x - Z1 @ cx, y - Z1 @ cy
    sxx = float((wt * xt**2).sum())
    if sxx <= 1e-12 * max(1, len(x)):
        return {"testable": False, "reason": "no residual variation in x"}
    b = float((wt * xt * yt).sum() / sxx)
    e = yt - b * xt
    sc = wt * xt * e / sxx
    n, k = len(y), Z1.shape[1] + 1
    adj = (n - 1) / max(n - k, 1)
    va, vd, v2 = _twoway(sc, ev, day)
    se_e, se_2 = math.sqrt(va * adj), math.sqrt(v2 * adj)
    z_e, z_2 = b / se_e if se_e > 0 else 0.0, b / se_2 if se_2 > 0 else 0.0
    out = {
        "testable": True,
        "beta": b,
        "se_event": se_e,
        "se_twoway": se_2,
        "se_day": math.sqrt(vd * adj),
        "z_event": z_e,
        "z_twoway": z_2,
        "n": int(n),
        "n_event": int(len(pd.unique(ev))),
        "n_day": int(len(pd.unique(day))),
        "weighted": w is not None,
    }
    if sign is not None:
        pe, p2 = float(norm.sf(sign * z_e)), float(norm.sf(sign * z_2))
        out.update(sign_tested=int(sign), p_event=pe, p_twoway=p2, p=max(pe, p2))
    out["p_two_sided_event"] = float(2 * norm.sf(abs(z_e)))
    # event-cluster bootstrap CI of the partial slope (partialling held fixed)
    codes, uniq = pd.factorize(ev)
    g = len(uniq)
    A = np.bincount(codes, weights=wt * xt * yt, minlength=g)
    B = np.bincount(codes, weights=wt * xt * xt, minlength=g)
    rng = np.random.default_rng(seed)
    bs = np.empty(n_boot)
    for i in range(n_boot):
        m = np.bincount(rng.integers(0, g, g), minlength=g)
        bs[i] = (m @ A) / max(m @ B, 1e-18)
    out["ci_event_boot"] = [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]
    return out


def mean_test(
    dv: np.ndarray,
    ev: np.ndarray,
    day: np.ndarray,
    sign: int = 1,
    n_boot: int = N_BOOT,
    seed: int = SEED,
    w: np.ndarray | None = None,
) -> dict:
    """(Weighted) mean of per-row values with CR SEs (event; two-way), one-sided p in ``sign``."""
    n = len(dv)
    wt = np.ones(n) if w is None else np.asarray(w, float)
    sw = float(wt.sum())
    mu = float(dv.mean()) if w is None else float((wt * dv).sum() / sw)
    sc = (dv - mu) / n if w is None else wt * (dv - mu) / sw
    va, vd, v2 = _twoway(sc, ev, day)
    se_e, se_2 = math.sqrt(va), math.sqrt(v2)
    z_e, z_2 = mu / se_e if se_e > 0 else 0.0, mu / se_2 if se_2 > 0 else 0.0
    pe, p2 = float(norm.sf(sign * z_e)), float(norm.sf(sign * z_2))
    codes, uniq = pd.factorize(ev)
    g = len(uniq)
    S = np.bincount(codes, weights=wt * dv, minlength=g)
    C = np.bincount(codes, weights=wt, minlength=g).astype(float)
    rng = np.random.default_rng(seed)
    bs = np.empty(n_boot)
    for i in range(n_boot):
        m = np.bincount(rng.integers(0, g, g), minlength=g)
        bs[i] = (m @ S) / max(m @ C, 1e-12)
    return {
        "testable": True,
        "mean": mu,
        "se_event": se_e,
        "se_twoway": se_2,
        "se_day": math.sqrt(vd),
        "z_event": z_e,
        "z_twoway": z_2,
        "sign_tested": int(sign),
        "p_event": pe,
        "p_twoway": p2,
        "p": max(pe, p2),
        "n": int(n),
        "n_event": int(g),
        "n_day": int(len(pd.unique(day))),
        "weighted": w is not None,
        "ci_event_boot": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
    }


def lgb_fit_predict(
    Xtr: np.ndarray, ytr: np.ndarray, Xte: np.ndarray, n_classes: int, threads: int
) -> np.ndarray:
    """``ml_explain.lgb_fit`` configuration (lr 0.1, 15 leaves, 100 rounds), any thread count."""
    import lightgbm as lgb

    params = {
        "objective": "binary" if n_classes == 2 else "multiclass",
        "learning_rate": 0.1,
        "num_leaves": 15,
        "min_data_in_leaf": 20,
        "lambda_l2": 1.0,
        "feature_fraction": 1.0,
        "seed": SEED,
        "deterministic": True,
        "force_row_wise": True,
        "num_threads": threads,
        "verbose": -1,
    }
    if n_classes > 2:
        params["num_class"] = n_classes
    b = lgb.train(params, lgb.Dataset(Xtr, ytr.astype(int)), num_boost_round=LGB_ROUNDS)
    p = b.predict(Xte)
    if n_classes == 2:
        p = np.column_stack([1 - p, p])
    p = np.clip(p, 1e-6, None)
    return p / p.sum(1, keepdims=True)


def logloss_rows(p: np.ndarray, y: np.ndarray) -> np.ndarray:
    return -np.log(np.clip(p[np.arange(len(y)), y.astype(int)], 1e-15, 1.0))


def benjamini_yekutieli(pvals: dict[str, float], m_total: int, q: float = BY_Q) -> dict:
    return ml_explain.benjamini_yekutieli(pvals, m_total, q)


def prior_test_count(path: Path = provenance.TRIALS_PATH) -> dict:
    """Declared cumulative-count rule: non-placebo ``ml_explain`` lines contribute ``n_tests`` (or
    ``multiple_testing.m_tests``); each non-placebo line of ``PRIOR_KIND_ONE`` contributes 1;
    model fits/scores, placebos, case timelines and earlier battery lines contribute 0 here (a
    battery line is counted through its own summary)."""
    out = {"ml_explain": 0}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("evidence_role") == "placebo":
                continue
            k = r.get("kind")
            if k == "ml_explain":
                if r.get("source") == "hypothesis_battery_1":
                    continue
                n = r.get("n_tests")
                if n is None:
                    n = (r.get("multiple_testing") or {}).get("m_tests", 0)
                out["ml_explain"] += int(n or 0)
            elif k in PRIOR_KIND_ONE:
                out[k] = out.get(k, 0) + 1
    out["total"] = int(sum(v for k, v in out.items() if k != "total"))
    return out


# =============================================================================================
# 3. Declared hypotheses
# =============================================================================================


@dataclass(frozen=True)
class Hyp:
    hid: str
    family: str
    test: str  # beta | dll | mean
    target: str  # d | ya | y3 | res
    h: int  # horizon hours (0 for resolution)
    x: tuple[str, ...]
    pop: str
    prior: int  # theory sign (+1/-1); for dll always +1 (ΔLL > 0)
    controls: tuple[str, ...] = ()
    scale: str = "sd"  # sd | raw (beta tests)
    text: str = ""
    economics: bool = True  # directional, so a cost check applies if it survives


def _H(*a, **k) -> Hyp:
    return Hyp(*a, **k)


POP_RULES: dict[str, str] = {  # declared populations (each also requires the base mask)
    "all": "",
    "book": "has_book",
    "book_prev": "has_book_prev",
    "n1h": "f_n_1h >= 1",
    "n2h": "f_n_2h >= 1",
    "n6h": "f_n_6h >= 1",
    "n24h": "f_n_24h >= 1",
    "n24h_7d": "f_n_24h >= 1 and f_N_7d > 0",
    "small6h": "f_n_small_6h == 1",
    "persist": "f_persist_6h defined",
    "nw": "nw_share_new7d defined",
    "fresh": "f_n_fresh_24h == 1",
    "fresh_extreme": "f_n_fresh_24h == 1 and (mid <= 0.20 or mid >= 0.80)",
    "top1": "f_top1_dir defined and f_n_wallets_24h >= 2",
    "win": "f_n_win_24h == 1",
    "lose": "f_n_lose_24h == 1",
    "nr": "f_nr_dev defined (complete neg-risk sum)",
    "nr_sib2": "f_sib_nr_d2h defined",
    "nr_sib24": "f_sib_nr_d24h defined",
    "co_sib2": "f_sib_d2h defined",
    "co_sib24": "f_sib_d24h defined",
    "ladder": "f_ladder_z defined",
    "ladder_v": "f_ladder_viol defined",
    "near72": "0 < hours_to_end <= 72",
    "mid35": "mid <= 0.35 and hours_to_end known",
    "res_long": "resolved binary market and mid <= 0.15",
    "res_fav": "resolved binary market and mid >= 0.85",
    "convex": "f_n_2h >= 3 and p_acq <= 0.20 and f_convex_pressure defined",
    "n2h3": "f_n_2h >= 3 and f_top1_share defined",
    "n6h_quiet": "f_n_6h >= 1 and f_quiet defined",
    "n6h_near": "f_n_6h >= 1 and f_near_end defined",
    "n24h_cov": "f_n_24h defined (24h trade window covered)",
}


def pop_mask(name: str, d: pd.DataFrame, base: pd.Series | None = None) -> pd.Series:
    """Declared population ``name`` within ``base`` (default: rows with a trade before t, the
    primary analysis; the untraded sensitivity passes an all-True base)."""
    b = d["traded"] if base is None else base
    nn = pd.Series.notna
    m = {
        "all": lambda: b,
        "book": lambda: d["has_book"],
        "book_prev": lambda: d["has_book_prev"],
        "n1h": lambda: d["f_n_1h"] >= 1,
        "n2h": lambda: d["f_n_2h"] >= 1,
        "n6h": lambda: d["f_n_6h"] >= 1,
        "n24h": lambda: d["f_n_24h"] >= 1,
        "n24h_7d": lambda: (d["f_n_24h"] >= 1) & (d["f_N_7d"] > 0),
        "small6h": lambda: d["f_n_small_6h"] == 1,
        "persist": lambda: nn(d["f_persist_6h"]),
        "nw": lambda: nn(d["nw_share_new7d"]) if "nw_share_new7d" in d else d["mid_i"] < -1,
        "fresh": lambda: d["f_n_fresh_24h"] == 1,
        "fresh_extreme": lambda: (d["f_n_fresh_24h"] == 1) & (d["f_extreme20"] == 1),
        "top1": lambda: nn(d["f_top1_dir"]) & (d["f_n_wallets_24h"] >= 2),
        "win": lambda: d["f_n_win_24h"] == 1,
        "lose": lambda: d["f_n_lose_24h"] == 1,
        "nr": lambda: nn(d["f_nr_dev"]),
        "nr_sib2": lambda: nn(d["f_sib_nr_d2h"]),
        "nr_sib24": lambda: nn(d["f_sib_nr_d24h"]),
        "co_sib2": lambda: nn(d["f_sib_d2h"]),
        "co_sib24": lambda: nn(d["f_sib_d24h"]),
        "ladder": lambda: nn(d["f_ladder_z"]),
        "ladder_v": lambda: nn(d["f_ladder_viol"]),
        "near72": lambda: d["f_near_end"] == 1,
        "mid35": lambda: (d["mid_i"] <= 0.35) & nn(d["f_near_end"]),
        "res_long": lambda: d["ok_res"] & (d["mid_i"] <= 0.15),
        "res_fav": lambda: d["ok_res"] & (d["mid_i"] >= 0.85),
        "convex": lambda: d["pop_convex"] & nn(d["f_convex_pressure"]),
        "n2h3": lambda: (d["f_n_2h"] >= 3) & nn(d["f_top1_share"]),
        "n6h_quiet": lambda: (d["f_n_6h"] >= 1) & nn(d["f_quiet"]),
        "n6h_near": lambda: (d["f_n_6h"] >= 1) & nn(d["f_near_end"]),
        "n24h_cov": lambda: nn(d["f_n_24h"]),
    }[name]()
    return (b & m).fillna(False).astype(bool)


FLOW = ("f_imb_6h",)
HYPOTHESES: tuple[Hyp, ...] = (
    # --- MS market state ------------------------------------------------------------------
    _H(
        "MS1",
        "market_state",
        "dll",
        "ya",
        6,
        ("f_log_age",),
        "all",
        1,
        text="log1p(market age h) adds to M0v for |move| 6h",
    ),
    _H(
        "MS2",
        "market_state",
        "dll",
        "ya",
        6,
        ("f_log_last_trade_age",),
        "all",
        1,
        text="log1p(hours since last trade, price-aligned) adds to M0v for |move| 6h",
    ),
    _H(
        "MS3",
        "market_state",
        "dll",
        "ya",
        6,
        ("f_vol_surprise",),
        "n24h_7d",
        1,
        text="24h notional vs own 7-day daily mean (log) adds to M0v for |move| 6h",
    ),
    _H(
        "MS4",
        "market_state",
        "beta",
        "d",
        24,
        ("f_vol_confirm",),
        "n24h_7d",
        1,
        controls=(*C0, "f_vol_surprise"),
        text="sign(1d change) x volume surprise predicts 24h continuation",
    ),
    # --- MI microstructure ----------------------------------------------------------------
    _H(
        "MI1",
        "microstructure",
        "beta",
        "d",
        2,
        ("f_rev_illiq",),
        "n24h_cov",
        -1,
        controls=(*C0, "f_illiq"),
        scale="raw",
        text="2h reversal stronger when 24h notional is below the discovery median",
    ),
    _H(
        "MI2",
        "microstructure",
        "beta",
        "d",
        2,
        ("f_rev_notrade",),
        "n24h_cov",
        -1,
        controls=(*C0, "f_no_trade_2h"),
        scale="raw",
        text="2h reversal stronger when the 2h move had no trade (quote noise)",
    ),
    _H(
        "MI3",
        "microstructure",
        "beta",
        "d",
        2,
        ("f_rev_vol",),
        "all",
        -1,
        controls=(*C0, "f_z_lrv1d"),
        scale="raw",
        text="2h reversal stronger at high 1d realised volatility",
    ),
    _H(
        "MI4",
        "microstructure",
        "beta",
        "d",
        2,
        ("f_rev_extreme",),
        "all",
        -1,
        controls=(*C0, "f_extreme"),
        scale="raw",
        text="2h reversal differs within 0.10 of 0/1",
    ),
    _H(
        "MI5",
        "microstructure",
        "beta",
        "d",
        2,
        ("f_rev_tte",),
        "all",
        -1,
        controls=(*C0, "f_z_lte"),
        scale="raw",
        text="2h reversal stronger further from scheduled end (E006 H2 analogue)",
    ),
    _H(
        "MI6",
        "microstructure",
        "beta",
        "d",
        2,
        ("f_rev_confirm",),
        "n24h_cov",
        1,
        controls=(*C0, "f_confirm"),
        scale="raw",
        text="a 2h move confirmed by same-sign 2h taker flow reverses less",
    ),
    _H(
        "MI7",
        "microstructure",
        "dll",
        "ya",
        2,
        ("f_spread_proxy",),
        "all",
        1,
        text="median |trade price - prevailing series price| over 24h adds to M0v for |move| 2h",
    ),
    _H(
        "MI8",
        "microstructure",
        "dll",
        "ya",
        6,
        ("bk_ml_sw_spread",),
        "book",
        1,
        text="pmxt book spread adds to M0v for |move| 6h",
    ),
    _H(
        "MI9",
        "microstructure",
        "beta",
        "d",
        6,
        ("bk_ml_sw_imb_1c",),
        "book",
        1,
        controls=C0,
        text="1c depth imbalance (bid - ask) predicts 6h drift",
    ),
    _H(
        "MI10",
        "microstructure",
        "beta",
        "d",
        6,
        ("bk_ml_sw_microprice_disp",),
        "book",
        1,
        controls=C0,
        text="microprice displacement predicts 6h drift",
    ),
    # --- FL flow ---------------------------------------------------------------------------
    _H(
        "FL1",
        "flow",
        "beta",
        "d",
        2,
        ("f_imb_1h",),
        "n1h",
        1,
        controls=C0,
        text="1h notional imbalance predicts 2h drift",
    ),
    _H(
        "FL2",
        "flow",
        "beta",
        "d",
        6,
        ("f_imb_6h",),
        "n6h",
        1,
        controls=C0,
        text="6h notional imbalance predicts 6h drift",
    ),
    _H(
        "FL3",
        "flow",
        "beta",
        "d",
        24,
        ("f_imb_24h",),
        "n24h",
        1,
        controls=C0,
        text="24h notional imbalance predicts 24h drift",
    ),
    _H(
        "FL4",
        "flow",
        "beta",
        "d",
        6,
        ("f_large_flow_6h",),
        "n6h",
        1,
        controls=C0,
        text="net notional of trades >= $500 over 6h (per mean daily notional) predicts 6h drift",
    ),
    _H(
        "FL5",
        "flow",
        "beta",
        "d",
        6,
        ("f_small_imb_6h",),
        "small6h",
        -1,
        controls=C0,
        text="imbalance of trades < $50 over 6h predicts 6h drift (retail: reversal prior)",
    ),
    _H(
        "FL6",
        "flow",
        "beta",
        "d",
        6,
        ("f_agg_flow_6h",),
        "n6h",
        1,
        controls=C0,
        text="net share of trades paying >= 1c through the prevailing price predicts 6h drift",
    ),
    _H(
        "FL7",
        "flow",
        "beta",
        "d",
        6,
        ("f_persist_6h",),
        "persist",
        1,
        controls=C0,
        scale="raw",
        text="three consecutive same-sign 2h flow windows predict 6h drift",
    ),
    _H(
        "FL8",
        "flow",
        "beta",
        "d",
        24,
        ("f_flow_surprise",),
        "n24h_7d",
        1,
        controls=C0,
        text="24h imbalance minus own 7d imbalance predicts 24h drift",
    ),
    _H(
        "FL9",
        "flow",
        "dll",
        "ya",
        6,
        ("f_burst_2h",),
        "n24h",
        1,
        text="2h trade count vs trailing 24h rate adds to M0v for |move| 6h",
    ),
    _H(
        "FL10",
        "flow",
        "beta",
        "d",
        24,
        ("f_imb_2h",),
        "n2h",
        1,
        controls=C0,
        text="2h notional imbalance predicts 24h drift",
    ),
    # --- WA wallet -------------------------------------------------------------------------
    _H(
        "WA1",
        "wallet",
        "dll",
        "ya",
        24,
        ("nw_share_new7d",),
        "nw",
        1,
        text="24h volume share of wallets < 7d old (true first trade) adds to M0v for |move| 24h",
    ),
    _H(
        "WA2",
        "wallet",
        "beta",
        "d",
        24,
        ("f_fresh_flow_24h",),
        "fresh",
        1,
        controls=C0,
        text="net notional share of fresh (< 7d) wallets over 24h predicts 24h drift",
    ),
    _H(
        "WA3",
        "wallet",
        "beta",
        "d",
        24,
        ("f_fresh_flow_24h",),
        "fresh_extreme",
        1,
        controls=C0,
        text="WA2 restricted to mid <= 0.20 or >= 0.80 (convex acquisition by fresh wallets)",
    ),
    _H(
        "WA4",
        "wallet",
        "beta",
        "d",
        24,
        ("f_top1_dir",),
        "top1",
        1,
        controls=C0,
        text="top wallet's 24h notional share x its net direction predicts 24h drift",
    ),
    _H(
        "WA5",
        "wallet",
        "dll",
        "ya",
        24,
        ("f_hhi_24h",),
        "n24h",
        1,
        text="24h wallet notional HHI adds to M0v for |move| 24h",
    ),
    _H(
        "WA6",
        "wallet",
        "beta",
        "d",
        24,
        ("f_win_flow_24h",),
        "win",
        1,
        controls=C0,
        text="net notional share of wallets with a positive causal record predicts 24h drift",
    ),
    _H(
        "WA7",
        "wallet",
        "beta",
        "d",
        24,
        ("f_lose_flow_24h",),
        "lose",
        -1,
        controls=C0,
        text="net notional share of wallets with a negative causal record predicts 24h drift",
    ),
    _H(
        "WA8",
        "wallet",
        "dll",
        "ya",
        24,
        ("f_n_new1d_24h",),
        "n24h_cov",
        1,
        text="number of wallets < 1d old trading in 24h adds to M0v for |move| 24h",
    ),
    # --- XM cross-market -------------------------------------------------------------------
    _H(
        "XM1",
        "cross_market",
        "beta",
        "d",
        6,
        ("f_nr_dev",),
        "nr",
        1,
        controls=C0,
        text="neg-risk sum deviation -(S-1)*mid/S predicts 6h drift",
    ),
    _H(
        "XM2",
        "cross_market",
        "dll",
        "ya",
        6,
        ("f_nr_absdev",),
        "nr",
        1,
        text="|neg-risk sum - 1| adds to M0v for |move| 6h",
    ),
    _H(
        "XM3",
        "cross_market",
        "beta",
        "d",
        2,
        ("f_sib_nr_d2h",),
        "nr_sib2",
        -1,
        controls=C0,
        text="sum of neg-risk siblings' 2h changes predicts own 2h drift",
    ),
    _H(
        "XM4",
        "cross_market",
        "beta",
        "d",
        2,
        ("f_sib_d2h",),
        "co_sib2",
        1,
        controls=C0,
        text="mean 2h change of non-neg-risk siblings predicts own 2h drift",
    ),
    _H(
        "XM5",
        "cross_market",
        "beta",
        "d",
        24,
        ("f_sib_nr_d24h",),
        "nr_sib24",
        -1,
        controls=C0,
        text="sum of neg-risk siblings' 24h changes predicts own 24h drift",
    ),
    _H(
        "XM6",
        "cross_market",
        "beta",
        "d",
        24,
        ("f_sib_d24h",),
        "co_sib24",
        1,
        controls=C0,
        text="mean 24h change of non-neg-risk siblings predicts own 24h drift",
    ),
    _H(
        "XM7",
        "cross_market",
        "beta",
        "d",
        24,
        ("f_ladder_z",),
        "ladder",
        1,
        controls=C0,
        text="IF-H2 decay-adjusted near/far ladder residual z predicts near-rung 24h drift",
    ),
    _H(
        "XM8",
        "cross_market",
        "beta",
        "d",
        6,
        ("f_ladder_viol",),
        "ladder_v",
        -1,
        controls=C0,
        text="near rung above the next later rung (monotonicity violation) predicts 6h fall",
    ),
    # --- TI time ---------------------------------------------------------------------------
    _H(
        "TI1",
        "time",
        "dll",
        "ya",
        2,
        ("f_hour_sin", "f_hour_cos"),
        "all",
        1,
        text="UTC hour of day adds to M0v for |move| 2h",
    ),
    _H(
        "TI2",
        "time",
        "dll",
        "ya",
        6,
        tuple(f"f_wd_{k}" for k in range(7)),
        "all",
        1,
        text="weekday adds to M0v for |move| 6h",
    ),
    _H(
        "TI3",
        "time",
        "beta",
        "d",
        24,
        ("f_mid_c",),
        "near72",
        1,
        controls=C0M,
        scale="raw",
        text="within 72h of scheduled end, mid - 0.5 predicts 24h drift (favourites up)",
    ),
    _H(
        "TI4",
        "time",
        "beta",
        "d",
        24,
        ("f_near_end",),
        "mid35",
        -1,
        controls=(*C0M, "ml_logit_mid"),
        scale="raw",
        text="for mid <= 0.35, being within 72h of scheduled end predicts 24h decay",
    ),
    _H(
        "TI5",
        "time",
        "beta",
        "d",
        2,
        ("f_rev_weekend",),
        "all",
        -1,
        controls=(*C0, "f_weekend"),
        scale="raw",
        text="2h reversal stronger at weekends (UTC)",
    ),
    # --- CA category and asymmetry -----------------------------------------------------------
    _H(
        "CA1",
        "category",
        "dll",
        "ya",
        6,
        tuple(
            f"f_cat_{c}"
            for c in (
                "sports",
                "crypto",
                "politics",
                "unknown",
                "economics",
                "culture",
                "finance",
                "tech",
                "weather",
                "mentions",
                "other",
            )
        ),
        "all",
        1,
        text="fee category adds to M0v for |move| 6h",
    ),
    _H(
        "CA2",
        "category",
        "dll",
        "y3",
        24,
        ("f_cls_asymmetric", "f_cls_public", "f_cls_other"),
        "all",
        1,
        text="asymmetry class adds to M0v for 3-class direction 24h",
    ),
    _H(
        "CA3",
        "category",
        "beta",
        "d",
        2,
        ("f_rev_asym",),
        "all",
        1,
        controls=(*C0, "f_asym"),
        scale="raw",
        text="2h reversal weaker in decision-asymmetric markets",
    ),
    _H(
        "CA4",
        "category",
        "beta",
        "d",
        24,
        ("f_flow_asym",),
        "n6h",
        1,
        controls=(*C0, "f_imb_6h", "f_asym"),
        text="6h flow predicts 24h drift more in decision-asymmetric markets",
    ),
    _H(
        "CA5",
        "category",
        "beta",
        "d",
        24,
        ("f_asym_longshot",),
        "all",
        -1,
        controls=(*C0, "f_asym", "f_low20"),
        scale="raw",
        text="longshots (mid <= 0.20) in decision-asymmetric markets drift differently",
    ),
    # --- PX price extremity ----------------------------------------------------------------
    _H(
        "PX1",
        "extremity",
        "beta",
        "d",
        24,
        ("f_longshot",),
        "all",
        -1,
        controls=C0M,
        scale="raw",
        text="mid <= 0.15 predicts 24h downward drift (favourite-longshot)",
    ),
    _H(
        "PX2",
        "extremity",
        "beta",
        "d",
        24,
        ("f_favourite",),
        "all",
        1,
        controls=C0M,
        scale="raw",
        text="mid >= 0.85 predicts 24h upward drift",
    ),
    _H(
        "PX3",
        "extremity",
        "mean",
        "res",
        0,
        (),
        "res_long",
        -1,
        text="resolution excess Y0 - mid < 0 for mid <= 0.15 (longshots overpriced)",
    ),
    _H(
        "PX4",
        "extremity",
        "mean",
        "res",
        0,
        (),
        "res_fav",
        1,
        text="resolution excess Y0 - mid > 0 for mid >= 0.85 (favourites underpriced)",
    ),
    _H(
        "PX5",
        "extremity",
        "beta",
        "d",
        24,
        ("f_mom_extreme",),
        "all",
        1,
        controls=(*C0, "f_extreme"),
        scale="raw",
        text="1d momentum continues within 0.10 of 0/1",
    ),
    _H(
        "PX6",
        "extremity",
        "beta",
        "d",
        24,
        ("f_flow_longshot",),
        "n24h",
        -1,
        controls=(*C0, "f_imb_24h", "f_low20"),
        text="24h flow at mid <= 0.20 (longshot buying) predicts 24h drift differently",
    ),
    # --- LQ liquidity events ---------------------------------------------------------------
    _H(
        "LQ1",
        "liquidity",
        "dll",
        "ya",
        6,
        ("f_bk_depth_chg",),
        "book_prev",
        1,
        text="6h change of 5c book depth adds to M0v for |move| 6h",
    ),
    _H(
        "LQ2",
        "liquidity",
        "beta",
        "d",
        6,
        ("f_bk_side_withdraw",),
        "book_prev",
        1,
        controls=C0,
        text="ask-side minus bid-side depth withdrawal over 6h predicts 6h drift",
    ),
    _H(
        "LQ3",
        "liquidity",
        "dll",
        "ya",
        6,
        ("f_bk_log_depth",),
        "book",
        1,
        text="log 5c book depth adds to M0v for |move| 6h",
    ),
    _H(
        "LQ4",
        "liquidity",
        "dll",
        "ya",
        6,
        ("f_bk_spread_chg",),
        "book_prev",
        1,
        text="6h spread change adds to M0v for |move| 6h",
    ),
    _H(
        "LQ5",
        "liquidity",
        "dll",
        "ya",
        6,
        ("f_illiq_surprise",),
        "n24h",
        1,
        text="Amihud illiquidity 24h vs 7d (log ratio) adds to M0v for |move| 6h",
    ),
    # --- VO volatility clustering ----------------------------------------------------------
    _H(
        "VO1",
        "volatility",
        "dll",
        "ya",
        6,
        ("f_jump_ratio",),
        "all",
        1,
        text="largest 10-min jump in 6h over 7d rv adds to M0v for |move| 6h",
    ),
    _H(
        "VO2",
        "volatility",
        "dll",
        "ya",
        6,
        ("f_vol_of_vol",),
        "all",
        1,
        text="dispersion of 2h rv over 24h adds to M0v for |move| 6h",
    ),
    _H(
        "VO3",
        "volatility",
        "dll",
        "ya",
        2,
        ("f_vol_ratio",),
        "all",
        1,
        text="rv 2h / rv 7d adds to M0v for |move| 2h",
    ),
    _H(
        "VO4",
        "volatility",
        "dll",
        "ya",
        6,
        ("f_hours_since_move",),
        "all",
        1,
        text="hours since the last >= 1c 10-min move adds to M0v for |move| 6h",
    ),
    _H(
        "VO5",
        "volatility",
        "beta",
        "d",
        24,
        ("f_semivar_asym",),
        "all",
        1,
        controls=C0,
        text="24h up minus down semivariance share predicts 24h drift",
    ),
    # --- IX theory interactions ------------------------------------------------------------
    _H(
        "IX1",
        "interaction",
        "beta",
        "d",
        24,
        ("f_convex_pressure",),
        "convex",
        1,
        controls=C0,
        text="convex longshot pressure (theory 4a) predicts 24h drift in its direction",
    ),
    _H(
        "IX2",
        "interaction",
        "beta",
        "d",
        24,
        ("f_pressure_noresp",),
        "n2h3",
        1,
        controls=(*C0, "f_imb_2h"),
        text="pressure without price response (theory 4b) predicts 24h continuation",
    ),
    _H(
        "IX3",
        "interaction",
        "beta",
        "d",
        24,
        ("f_flow_quiet",),
        "n6h_quiet",
        1,
        controls=(*C0, "f_imb_6h", "f_quiet"),
        text="6h flow in a quiet market (24h notional below own 29-day median) predicts more",
    ),
    _H(
        "IX4",
        "interaction",
        "beta",
        "d",
        6,
        ("f_flow_near_end",),
        "n6h_near",
        1,
        controls=(*C0, "f_imb_6h", "f_near_end"),
        text="6h flow predicts 6h drift more within 72h of scheduled end",
    ),
    _H(
        "IX5",
        "interaction",
        "beta",
        "d",
        24,
        ("f_convex_dir",),
        "n24h_cov",
        1,
        controls=C0,
        scale="raw",
        text="net direction of >= $1,000 trades acquiring an outcome at <= 0.20",
    ),
    _H(
        "IX6",
        "interaction",
        "beta",
        "d",
        24,
        ("f_fresh_asym",),
        "fresh",
        1,
        controls=(*C0, "f_fresh_flow_24h", "f_asym"),
        text="fresh-wallet flow predicts more in decision-asymmetric markets",
    ),
)

assert len({h.hid for h in HYPOTHESES}) == len(HYPOTHESES)


def declaration_table() -> list[dict]:
    return [
        {
            "id": h.hid,
            "family": h.family,
            "test": h.test,
            "target": h.target,
            "h": h.h,
            "x": list(h.x),
            "pop": h.pop,
            "prior": h.prior,
            "controls": list(h.controls),
            "scale": h.scale,
            "text": h.text,
        }
        for h in HYPOTHESES
    ]


def declaration_sha256() -> str:
    import hashlib

    blob = json.dumps(
        {"version": VERSION, "split": SPLIT_TS, "embargo": EMBARGO_S, "hyps": declaration_table()},
        sort_keys=True,
    ).encode()
    return hashlib.sha256(blob).hexdigest()


# =============================================================================================
# 4. Running one hypothesis
# =============================================================================================


def _target(d: pd.DataFrame, h: Hyp) -> tuple[np.ndarray, pd.Series]:
    if h.target == "res":
        return d["res_excess"].to_numpy(float), d["ok_res"]
    col = {"d": "d_", "ya": "ya_", "y3": "y3_"}[h.target] + str(h.h)
    return d[col].to_numpy(float), d[f"ok_{h.h}"]


def _xform(x: np.ndarray, disc_mask: np.ndarray, scale: str) -> tuple[np.ndarray, dict]:
    if scale == "raw":
        return x, {"scale": "raw"}
    xd = x[disc_mask & np.isfinite(x)]
    if len(xd) < 10:
        return x, {"scale": "raw(fallback)"}
    nz = xd[xd != 0]
    if (xd == 0).mean() >= 0.5 and len(nz) >= 10:  # sparse feature: winsorise the non-zeros
        lo, hi = np.percentile(nz, [1, 99])
        lo, hi = min(lo, 0.0), max(hi, 0.0)
    else:
        lo, hi = np.percentile(xd, [1, 99])
    xw = np.clip(x, lo, hi)
    sd = float(np.std(np.clip(xd, lo, hi)))
    if sd <= 0:
        return x, {"scale": "raw(zero sd)"}
    return xw / sd, {"scale": "sd", "winsor": [float(lo), float(hi)], "sd": sd}


def run_beta(d: pd.DataFrame, h: Hyp, mask: pd.Series, n_boot: int, y_override=None) -> dict:
    y_all, ok = _target(d, h)
    if y_override is not None:
        y_all = y_override
    x_all = d[h.x[0]].to_numpy(float)
    m = (mask & ok).to_numpy() & np.isfinite(y_all) & np.isfinite(x_all)
    disc = m & (d["split"] == "disc").to_numpy()
    judge = m & (d["split"] == "judge").to_numpy()
    xs, sc = _xform(x_all, disc, h.scale)
    Z_all = d[list(h.controls)].to_numpy(float) if h.controls else np.empty((len(d), 0))
    zok = np.all(np.isfinite(Z_all), axis=1) if h.controls else np.ones(len(d), bool)
    disc, judge = disc & zok, judge & zok
    ev, day = d["event_c"].to_numpy(), d["day_c"].to_numpy()
    res = {"scaling": sc, "n_disc": int(disc.sum()), "n_judge": int(judge.sum())}
    nzj = judge & (xs != 0)
    res["n_judge_nonzero"] = int(nzj.sum())
    res["n_judge_nonzero_events"] = int(len(pd.unique(ev[nzj])))
    sign = h.prior
    if disc.sum() >= MIN_JUDGE_ROWS and len(pd.unique(ev[disc])) >= MIN_JUDGE_CLUSTERS:
        rd = beta_test(y_all[disc], xs[disc], Z_all[disc], ev[disc], day[disc], None, n_boot=200)
        res["discovery"] = rd
        if rd.get("testable") and rd["beta"] != 0:
            sign = int(np.sign(rd["beta"]))
            res["sign_source"] = "discovery"
        else:
            res["sign_source"] = "prior (discovery untestable)"
    else:
        res["sign_source"] = "prior (discovery too small)"
    res["sign_tested"] = sign
    if (
        judge.sum() < MIN_JUDGE_ROWS
        or len(pd.unique(ev[judge])) < MIN_JUDGE_CLUSTERS
        or res["n_judge_nonzero"] < MIN_NONZERO_ROWS
        or res["n_judge_nonzero_events"] < MIN_NONZERO_CLUSTERS
    ):
        res.update(testable=False, p=1.0, reason="judgement too small (rows/clusters/nonzero)")
        return res
    rj = beta_test(
        y_all[judge], xs[judge], Z_all[judge], ev[judge], day[judge], sign, n_boot=n_boot
    )
    res.update(rj)
    if not rj.get("testable"):
        res["p"] = 1.0
    res["effect"] = rj.get("beta")
    res["effect_unit"] = (
        "price points per 1 SD of x" if sc.get("scale") == "sd" else "price points per unit of x"
    )
    res["_masks"] = (disc, judge, xs)
    return res


def run_mean(d: pd.DataFrame, h: Hyp, mask: pd.Series, n_boot: int, y_override=None) -> dict:
    y_all, ok = _target(d, h)
    if y_override is not None:
        y_all = y_override
    m = (mask & ok).to_numpy() & np.isfinite(y_all)
    disc = m & (d["split"] == "disc").to_numpy()
    judge = m & (d["split"] == "judge").to_numpy()
    ev, day = d["event_c"].to_numpy(), d["day_c"].to_numpy()
    res = {"n_disc": int(disc.sum()), "n_judge": int(judge.sum())}
    sign = h.prior
    if disc.sum() >= MIN_JUDGE_ROWS and len(pd.unique(ev[disc])) >= MIN_JUDGE_CLUSTERS:
        rd = mean_test(y_all[disc], ev[disc], day[disc], 1, n_boot=200)
        res["discovery"] = rd
        if rd["mean"] != 0:
            sign = int(np.sign(rd["mean"]))
            res["sign_source"] = "discovery"
    else:
        res["sign_source"] = "prior (discovery too small)"
    res["sign_tested"] = sign
    if judge.sum() < MIN_JUDGE_ROWS or len(pd.unique(ev[judge])) < MIN_JUDGE_CLUSTERS:
        res.update(testable=False, p=1.0, reason="judgement too small")
        return res
    rj = mean_test(y_all[judge], ev[judge], day[judge], sign, n_boot=n_boot)
    res.update(rj)
    res["effect"] = rj["mean"]
    res["effect_unit"] = "mean resolution excess (payout - mid), probability points"
    return res


def run_dll(
    d: pd.DataFrame,
    h: Hyp,
    mask: pd.Series,
    n_boot: int,
    threads: int,
    cache: dict,
    y_override=None,
    tag: str = "",
) -> dict:
    y_all, ok = _target(d, h)
    if y_override is not None:
        y_all = y_override
    m = (mask & ok).to_numpy() & np.isfinite(y_all)
    disc = m & (d["split"] == "disc").to_numpy()
    judge = m & (d["split"] == "judge").to_numpy()
    ev, day = d["event_c"].to_numpy(), d["day_c"].to_numpy()
    res = {"n_disc": int(disc.sum()), "n_judge": int(judge.sum())}
    if (
        disc.sum() < MIN_DISC_ROWS_DLL
        or judge.sum() < MIN_JUDGE_ROWS
        or len(pd.unique(ev[judge])) < MIN_JUDGE_CLUSTERS
    ):
        res.update(testable=False, p=1.0, reason="too few rows/clusters")
        return res
    ncls = 3 if h.target == "y3" else 2
    y = y_all.astype(float)
    Xb = d[list(M0V)].to_numpy(float)
    key = (tag, h.pop, h.target, h.h)
    if key not in cache:
        cache[key] = lgb_fit_predict(Xb[disc], y[disc], Xb[judge], ncls, threads)
    pb = cache[key]
    Xf = np.column_stack([Xb, d[list(h.x)].to_numpy(float)])
    pf = lgb_fit_predict(Xf[disc], y[disc], Xf[judge], ncls, threads)
    yj = y[judge].astype(int)
    lb, lf = logloss_rows(pb, yj), logloss_rows(pf, yj)
    dv = lb - lf
    rj = mean_test(dv, ev[judge], day[judge], 1, n_boot=n_boot)
    res.update(rj)
    res["sign_tested"] = 1
    res["base_loss"] = float(lb.mean())
    res["full_loss"] = float(lf.mean())
    res["effect"] = rj["mean"]
    res["effect_rel"] = float(rj["mean"] / lb.mean()) if lb.mean() > 0 else None
    res["effect_unit"] = "ΔLL nats per judgement row (M0v minus M0v+x)"
    res["_pred"] = (judge, pb, pf)
    return res


# =============================================================================================
# 5. Robustness, placebo and economics for survivors
# =============================================================================================


def _subset_beta(d, h, mask, sub: np.ndarray, n_boot: int = 500) -> dict:
    y_all, ok = _target(d, h)
    x_all = d[h.x[0]].to_numpy(float)
    m = (mask & ok).to_numpy() & np.isfinite(y_all) & np.isfinite(x_all) & sub
    Z = d[list(h.controls)].to_numpy(float) if h.controls else np.empty((len(d), 0))
    if h.controls:
        m &= np.all(np.isfinite(Z), axis=1)
    ev, day = d["event_c"].to_numpy(), d["day_c"].to_numpy()
    disc0 = (mask & ok).to_numpy() & np.isfinite(x_all) & (d["split"] == "disc").to_numpy()
    xs, _ = _xform(x_all, disc0, h.scale)
    if m.sum() < 100 or len(pd.unique(ev[m])) < 10 or np.nanstd(xs[m]) == 0:
        return {"testable": False, "n": int(m.sum())}
    r = beta_test(y_all[m], xs[m], Z[m], ev[m], day[m], None, n_boot=n_boot)
    return (
        {k: r[k] for k in ("beta", "se_event", "ci_event_boot", "n", "n_event")}
        if r.get("testable")
        else {"testable": False}
    )


def robustness_beta(d: pd.DataFrame, h: Hyp, res: dict, d_shift: pd.DataFrame | None) -> dict:
    mask = pop_mask(h.pop, d)
    judge = (d["split"] == "judge").to_numpy()
    out: dict = {"by_category": {}, "by_month": {}}
    for c in sorted(d.loc[judge, "fee_cat"].dropna().unique()):
        out["by_category"][c] = _subset_beta(d, h, mask, judge & (d["fee_cat"] == c).to_numpy())
    for mo in sorted(d.loc[judge, "month"].unique()):
        out["by_month"][mo] = _subset_beta(d, h, mask, judge & (d["month"] == mo).to_numpy())
    untr = pop_mask(h.pop, d, base=pd.Series(True, index=d.index))  # keep untraded rows
    out["including_untraded"] = _subset_beta(d, h, untr, judge)
    recent = (d["f_n_24h"] >= 1).to_numpy()
    out["only_trade_in_prior_24h"] = _subset_beta(d, h, mask, judge & recent)
    if d_shift is not None and h.family in ("flow", "wallet", "interaction", "category"):
        out["staleness_flow_window_end_minus_30min"] = _subset_beta(
            d_shift, h, pop_mask(h.pop, d_shift), (d_shift["split"] == "judge").to_numpy()
        )
    # within-period permutation of the control-residualised feature (Freedman-Lane style, 200
    # draws): null distribution of the judgement slope with the controls' fit held fixed
    y_all, ok = _target(d, h)
    disc, jm, xs = res["_masks"]
    Z = d[list(h.controls)].to_numpy(float) if h.controls else np.empty((len(d), 0))
    yj, xj, Zj = y_all[jm], xs[jm], Z[jm]
    per = d["t_i"].to_numpy()[jm]
    Z1 = np.column_stack([np.ones(len(yj)), Zj]) if Zj.size else np.ones((len(yj), 1))
    yt = _resid(yj, Z1)
    xt0 = _resid(xj, Z1)
    sxx = max(float((xt0**2).sum()), 1e-18)
    rng = np.random.default_rng(SEED + 7)
    order = np.argsort(per, kind="stable")
    bounds = np.flatnonzero(np.diff(per[order])) + 1
    groups = np.split(order, bounds)
    null = []
    for _ in range(200):
        xp = xt0.copy()
        for g in groups:
            if len(g) > 1:
                xp[g] = xt0[rng.permutation(g)]
        null.append(float((xp * yt).sum() / sxx))
    null = np.array(null)
    b = res["beta"]
    out["permutation_within_period"] = {
        "n_draws": 200,
        "null_mean": float(null.mean()),
        "null_sd": float(null.std()),
        "p_one_sided": float(((res["sign_tested"] * null) >= res["sign_tested"] * b).mean()),
        "observed": b,
    }
    return out


def robustness_dll(d: pd.DataFrame, h: Hyp, res: dict) -> dict:
    judge, pb, pf = res["_pred"]
    y_all, _ = _target(d, h)
    yj = y_all[judge].astype(int)
    dv = logloss_rows(pb, yj) - logloss_rows(pf, yj)
    sub = d.loc[judge]
    ev = sub["event_c"].to_numpy()
    out: dict = {"by_category": {}, "by_month": {}}
    for key, col in (("by_category", "fee_cat"), ("by_month", "month")):
        for v, idx in sub.groupby(col).indices.items():
            if len(idx) < 100 or len(pd.unique(ev[idx])) < 10:
                continue
            r = mean_test(dv[idx], ev[idx], sub["day_c"].to_numpy()[idx], 1, n_boot=500)
            out[key][str(v)] = {k: r[k] for k in ("mean", "ci_event_boot", "n", "n_event")}
    rec = (sub["f_n_24h"] >= 1).to_numpy()
    if rec.sum() >= 100:
        r = mean_test(dv[rec], ev[rec], sub["day_c"].to_numpy()[rec], 1, n_boot=500)
        out["only_trade_in_prior_24h"] = {
            k: r[k] for k in ("mean", "ci_event_boot", "n", "n_event")
        }
    out["including_untraded"] = "not computed: models are fitted on traded rows only (declared)"
    return out


def fee_rate(cat: str) -> float:
    if cat in NO_FEE_CATEGORIES or str(cat).split(":")[0] == "unknown":
        return 0.0
    r = economics._docs_rate(cat)
    return economics.MAX_DOCS_RATE if math.isnan(r) else r


def economics_check(d: pd.DataFrame, h: Hyp, res: dict) -> dict:
    """Cost-aware check for a directional survivor (paper only, optimistic, not tradable).

    beta: signal s = beta_disc * x (scaled), trade sign(s) where |s| >= the 90th percentile of |s|
    on discovery rows. dll (3-class): signal = incremental P(up)-P(down) tilt, trade the top decile
    of |tilt| among judgement rows (feature-only threshold). Gross = sign * d_h per share; cost =
    spread (pmxt book at the origin when present, else EXECUTION_COSTS band median) + taker fee on
    entry and exit at the docs category rate (current fee era, conservative for older rows)."""
    if h.test == "mean" or (h.test == "dll" and h.target != "y3") or not h.economics:
        return {
            "applicable": False,
            "reason": "no directional trade rule (volatility or resolution-level test)",
        }
    y_all = d[f"d_{h.h}"].to_numpy(float)  # gross P&L always from the mid change
    if h.test == "beta":
        disc, judge, xs = res["_masks"]
        bd_ = res.get("discovery", {}).get("beta")
        if bd_ is None:
            return {"applicable": False, "reason": "no discovery slope"}
        s = bd_ * xs
        tau = float(np.percentile(np.abs(s[disc]), 90))
        pick = judge & (np.abs(s) >= tau) & (s != 0)
        sgn = np.sign(s[pick])
    else:
        judge, pb, pf = res["_pred"]
        tilt = (pf[:, 2] - pf[:, 0]) - (pb[:, 2] - pb[:, 0])
        tau = float(np.percentile(np.abs(tilt), 90))
        full_tilt = np.zeros(len(d))
        full_tilt[judge] = tilt
        pick = judge & (np.abs(full_tilt) >= tau)
        sgn = np.sign(full_tilt[pick])
    if pick.sum() < 30:
        return {"applicable": True, "testable": False, "n_trades": int(pick.sum())}
    sub = d.loc[pick]
    m0 = sub["mid_i"].to_numpy(float)
    m1 = m0 + y_all[pick]
    gross = sgn * y_all[pick]
    book_sp = (sub["bk_sw_best_ask"] - sub["bk_sw_best_bid"]).to_numpy(float)
    spread = np.where(np.isfinite(book_sp) & (book_sp > 0), book_sp, _band_spread(m0))
    rates = np.array([fee_rate(c) for c in sub["fee_category"].fillna("unknown")])
    pe = np.where(sgn > 0, m0, 1 - m0)
    px = np.clip(np.where(sgn > 0, m1, 1 - m1), 0, 1)
    fee = rates * (pe * (1 - pe) + px * (1 - px))
    net = gross - spread - fee
    net_opt = gross - spread / 2.0
    ev, day = sub["event_c"].to_numpy(), sub["day_c"].to_numpy()
    rn = mean_test(net, ev, day, 1, n_boot=1000)
    rg = mean_test(gross, ev, day, 1, n_boot=1000)
    ro = mean_test(net_opt, ev, day, 1, n_boot=1000)
    return {
        "applicable": True,
        "testable": True,
        "threshold_abs_signal": tau,
        "n_trades": int(pick.sum()),
        "n_events": rn["n_event"],
        "share_with_book_spread": float(np.mean(np.isfinite(book_sp) & (book_sp > 0))),
        "mean_gross": rg["mean"],
        "gross_ci": rg["ci_event_boot"],
        "mean_spread": float(spread.mean()),
        "mean_fee": float(fee.mean()),
        "mean_net_taker": rn["mean"],
        "net_taker_ci": rn["ci_event_boot"],
        "p_net_taker_gt0": rn["p"],
        "mean_net_half_spread_no_fee": ro["mean"],
        "net_half_spread_ci": ro["ci_event_boot"],
        "hit_rate": float((gross > 0).mean()),
        "note": "paper only, optimistic: mid-to-mid gross, no latency, no depth beyond touch",
    }


# =============================================================================================
# 6. Orchestration
# =============================================================================================


def run_all(
    d: pd.DataFrame,
    n_boot: int,
    threads: int,
    log,
    only: set[str] | None = None,
    y_perm_seed: int | None = None,
) -> dict:
    """Run every declared hypothesis. ``y_perm_seed``: globally permute every target first
    (calibration placebo; nothing about outcomes is learned)."""
    results: dict = {}
    cache: dict = {}
    overrides = {}
    if y_perm_seed is not None:
        rng = np.random.default_rng(y_perm_seed)
        for col in (
            "d_2",
            "d_6",
            "d_24",
            "ya_2",
            "ya_6",
            "ya_24",
            "y3_2",
            "y3_6",
            "y3_24",
            "res_excess",
        ):
            v = d[col].to_numpy(float).copy()
            fin = np.isfinite(v)
            v[fin] = v[fin][rng.permutation(fin.sum())]
            overrides[col] = v
    for h in HYPOTHESES:
        if only and h.hid not in only:
            continue
        t0 = time.time()
        mask = pop_mask(h.pop, d)
        yo = None
        if overrides:
            col = {"d": f"d_{h.h}", "ya": f"ya_{h.h}", "y3": f"y3_{h.h}"}.get(
                h.target, "res_excess"
            )
            yo = overrides[col]
        if h.test == "beta":
            r = run_beta(d, h, mask, n_boot, y_override=yo)
        elif h.test == "mean":
            r = run_mean(d, h, mask, n_boot, y_override=yo)
        else:
            r = run_dll(
                d, h, mask, n_boot, threads, cache, y_override=yo, tag="perm" if overrides else ""
            )
        r["seconds"] = round(time.time() - t0, 1)
        results[h.hid] = r
        log(
            f"  {h.hid:5s} {h.test:4s} p={r.get('p', 1.0):.3g} eff={r.get('effect')} "
            f"n_j={r.get('n_judge')} ({r['seconds']}s)"
        )
    return results


def apply_by(results: dict, m_total: int) -> dict:
    ps = {k: float(v.get("p", 1.0) if v.get("testable", True) else 1.0) for k, v in results.items()}
    by = benjamini_yekutieli(ps, m_total, BY_Q)
    within = benjamini_yekutieli(ps, len(ps), BY_Q)
    for k, v in results.items():
        v["p_by_cumulative"] = by[k]["p_by"]
        v["pass_by_cumulative"] = by[k]["pass_by"]
        v["p_by_within_battery"] = within[k]["p_by"]
        v["pass_by_within_battery"] = within[k]["pass_by"]
    return {
        "m_total": m_total,
        "m_battery": len(ps),
        "q": BY_Q,
        "survivors": sorted(k for k, v in results.items() if v["pass_by_cumulative"]),
        "within_battery_survivors": sorted(
            k for k, v in results.items() if v["pass_by_within_battery"]
        ),
    }


def _clean(o):
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items() if not str(k).startswith("_")}
    if isinstance(o, list | tuple):
        return [_clean(v) for v in o]
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, float) and not math.isfinite(o):
        return None
    return o


def coverage_report(d: pd.DataFrame) -> dict:
    out = {}
    for h in HYPOTHESES:
        m = pop_mask(h.pop, d)
        ok = d[f"ok_{h.h}"] if h.target != "res" else d["ok_res"]
        mm = m & ok
        if h.x:
            mm &= d[list(h.x)].notna().all(axis=1) if h.test != "dll" else True
        out[h.hid] = {
            "disc": int((mm & (d["split"] == "disc")).sum()),
            "judge": int((mm & (d["split"] == "judge")).sum()),
            "judge_events": int(d.loc[mm & (d["split"] == "judge"), "event_c"].nunique()),
        }
    return out


def read_features(path: Path, columns: list[str] | None = None) -> pd.DataFrame:
    """Read a feature table and turn nullable string columns back into plain object columns, so
    comparisons give numpy booleans."""
    d = pd.read_parquet(path, columns=columns)
    for c in d.columns:
        if isinstance(d[c].dtype, pd.StringDtype):
            d[c] = d[c].astype(object).where(d[c].notna(), None)
    return d


def _to_parquet_safe(d: pd.DataFrame) -> pd.DataFrame:
    """Object columns (strings with NaN from left joins) as nullable strings for parquet."""
    for c in d.columns:
        if d[c].dtype == object:
            d[c] = d[c].astype("string")
    return d


def cli(cmd: str, a, out_dir: Path, run_dir: Path, log) -> int:
    feat_path = out_dir / "features.parquet"
    shift_path = out_dir / "features_shift30.parquet"
    if cmd == "features":
        d = _to_parquet_safe(build_features(run_dir, out_dir, log))
        d.to_parquet(feat_path, index=False)
        log(f"features: {len(d)} rows, {d.shape[1]} columns -> {feat_path}")
        del d
        ds = _to_parquet_safe(build_features(run_dir, out_dir, log, shift_s=1800.0))
        ds.to_parquet(shift_path, index=False)
        log(f"features (flow windows ending 30 min earlier) -> {shift_path}")
        return 0
    d = read_features(feat_path)
    cuts = fit_cuts(d)
    d = apply_cuts(d, cuts)
    only = {x for x in a.only.split(",") if x} or None
    if cmd == "dryrun":
        log("DRY RUN on globally permuted targets (calibration placebo)")
        cov = coverage_report(d)
        res = run_all(d, min(a.n_boot, 200), a.threads, log, only, y_perm_seed=SEED + 1)
        summ = apply_by(res, len(res))
        (out_dir / "dryrun_results.json").write_text(
            json.dumps(
                _clean({"coverage": cov, "results": res, "by": summ, "cuts": cuts}), indent=1
            )
        )
        log(json.dumps(summ))
        return 0
    if cmd == "run":
        return run_main(d, cuts, a, out_dir, shift_path, log)
    raise ValueError(cmd)


def run_main(d: pd.DataFrame, cuts: dict, a, out_dir: Path, shift_path: Path, log) -> int:
    prior = prior_test_count()
    m_total = prior["total"] + len(HYPOTHESES)
    log(f"prior tests {prior}; m_total {m_total}; declaration sha {declaration_sha256()}")
    only = {x for x in a.only.split(",") if x} or None
    res = run_all(d, a.n_boot, a.threads, log, only)
    summ = apply_by(res, m_total)
    log(f"BY survivors (cumulative m={m_total}): {summ['survivors']}")
    ds = None
    hmap0 = {h.hid: h for h in HYPOTHESES}
    need_shift = [
        hid
        for hid in summ["survivors"]
        if hmap0[hid].test == "beta"
        and hmap0[hid].family in ("flow", "wallet", "interaction", "category")
    ]
    if shift_path.exists() and need_shift:
        ds = apply_cuts(read_features(shift_path), cuts)
    hmap = {h.hid: h for h in HYPOTHESES}
    extra = {}
    for hid in summ["survivors"]:
        h = hmap[hid]
        r = res[hid]
        log(f"  robustness/economics for {hid}")
        rob = (
            robustness_beta(d, h, r, ds)
            if h.test == "beta"
            else robustness_dll(d, h, r)
            if h.test == "dll"
            else {}
        )
        extra[hid] = {"robustness": rob, "economics": economics_check(d, h, r)}
    log("calibration placebo: whole battery on globally permuted targets")
    plc = run_all(d, 200, a.threads, log, only, y_perm_seed=SEED + 1)
    plc_by = apply_by(plc, m_total)
    out = {
        "version": VERSION,
        "revision": REVISION,
        "evidence_role": EVIDENCE_ROLE,
        "declaration_sha256": declaration_sha256(),
        "split_ts": SPLIT_TS,
        "embargo_s": EMBARGO_S,
        "prior_tests": prior,
        "m_total": m_total,
        "cuts": cuts,
        "results": res,
        "by": summ,
        "survivor_checks": extra,
        "placebo_global_permutation": {
            "by": plc_by,
            "p_values": {k: v.get("p") for k, v in plc.items()},
        },
        "provenance": provenance.run_provenance(),
    }
    path = out_dir / "results_hb1.json"
    path.write_text(json.dumps(_clean(out), indent=1))
    log_trials(out, path)
    log(f"wrote {path}")
    return 0


def log_trials(out: dict, path: Path) -> None:
    sha = provenance.sha256_file(path)
    hmap = {h.hid: h for h in HYPOTHESES}
    for hid, r in out["results"].items():
        h = hmap[hid]
        provenance.append_trial(
            {
                "kind": TRIAL_KIND,
                "label": "EXPLORATORY",
                "evidence_role": EVIDENCE_ROLE,
                "revision": REVISION,
                "dataset": "history:h2_main",
                "hypothesis": hid,
                "family": h.family,
                "test": h.test,
                "target": h.target,
                "horizon_hours": h.h,
                "features": list(h.x),
                "population": h.pop,
                "sign_tested": r.get("sign_tested"),
                "effect": _clean(r.get("effect")),
                "p": _clean(r.get("p")),
                "p_by_cumulative": _clean(r.get("p_by_cumulative")),
                "pass_by_cumulative": r.get("pass_by_cumulative"),
                "testable": r.get("testable", True),
                "n_judge": r.get("n_judge"),
                "m_total": out["m_total"],
                "declaration_sha256": out["declaration_sha256"],
                "results_sha256": sha,
                "data_provenance": hb.PROVENANCE,
            }
        )
    fam: dict[str, int] = {}
    for h in HYPOTHESES:
        fam[f"hb1:{h.family}"] = fam.get(f"hb1:{h.family}", 0) + 1
    provenance.append_trial(
        {
            "kind": "ml_explain",
            "label": "EXPLORATORY",
            "evidence_role": EVIDENCE_ROLE,
            "source": "hypothesis_battery_1",
            "revision": REVISION,
            "dataset": "history:h2_main",
            "n_tests": len(HYPOTHESES),
            "n_tests_by_family": fam,
            "multiple_testing": {
                "by_q": BY_Q,
                "m_tests": len(HYPOTHESES),
                "prior_tests": out["prior_tests"]["total"],
                "m_total": out["m_total"],
            },
            "survivors": out["by"]["survivors"],
            "declaration_sha256": out["declaration_sha256"],
            "results_sha256": sha,
            "data_provenance": hb.PROVENANCE,
            "note": "HB1 summary: counts its tests into the cumulative ml_explain BY denominator",
        }
    )
