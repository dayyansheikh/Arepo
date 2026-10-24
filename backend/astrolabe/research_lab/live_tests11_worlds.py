# ruff: noqa: E501
"""LT11 simulated worlds 1-15 and the size check (LIVE_TESTS_11.md 1.8, 1.8.1). Research tooling only; no data is read; no network.

LT11 ambiguity A10: the worlds generate the ANALYSIS FRAME directly (the columns the primary model reads, with the declared controls computed from the simulated
paths in this module), not raw snapshot captures pushed through the reader's builders as LT10's worlds do. The gate path (``b.block_fl_gate`` for CH234 and
CH232, ``analysis.event_index_fl_gate`` for CH233), the minima (16), the estimator (``analysis.fit11``) and the F rule / point condition (``analysis.f_rule`` /
``analysis.point_condition``) are the analysis'; the world generators are conventions (1.8.1) and are not tuned after any result.
"""

from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
from scipy.signal import lfilter
from scipy.special import expit, logit, ndtr

from . import bounce_decomp as bd
from . import live_tests11 as lt
from . import live_tests11_analysis as an
from . import live_tests11_base as b

TESTS = lt.TESTS
REGISTERED_SEED = 20261497
DEV_SEED = REGISTERED_SEED * 100 + 99  # development runs never use the registered seed (1.8: no preliminary run at 20261497)
SLOT_S = 7200.0
T0 = float(lt.epoch("2026-11-18T00:00:00Z"))
SCENARIO_ORDER = ("1", "2", "3", "3b", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15")
SCENARIOS: dict[str, dict] = {
    **{s: {"test": "CH234", "stat": "gate"} for s in ("1", "2", "3", "3b", "4")},
    **{s: {"test": "CH233", "stat": "gate"} for s in ("5", "6", "7", "8")},
    **{s: {"test": "CH232", "stat": "gate"} for s in ("9", "10", "11", "15")},
    "12": {"test": "CH234", "stat": "verdict"}, "13": {"test": "CH233", "stat": "verdict"}, "14": {"test": "CH232", "stat": "verdict"},
}
POWER = {"CH234": ("0.5c per census tercile gap of xw", 0.5, 41), "CH233": ("1.0c per tercile gap of z cl_sib", 1.0, 42), "CH232": ("1.0c between classes", 1.0, 43)}


class Refused(RuntimeError):
    """The size check refuses (a registered seed on a development run, an unknown scenario, an unfilled census value)."""


FROZEN_LIMIT = 0.058  # 1.8: "limit 0.058" at 2,000 worlds (the formula gives 0.058017; the frozen value is used)
FROZEN_WORLDS = 2000


def limit_for(worlds: int) -> float:
    """1.8's criterion: the frozen 0.058 at the registered 2,000 worlds; ``0.05 + 1.645 sqrt(0.0475 / worlds)`` for development sizes only."""
    return FROZEN_LIMIT if worlds == FROZEN_WORLDS else 0.05 + 1.645 * math.sqrt(0.0475 / worlds)


def ar1(rng, shape, rho: float, sd: float = 1.0) -> np.ndarray:
    e = rng.normal(0.0, sd * math.sqrt(1.0 - rho**2), shape)
    e[..., 0] = rng.normal(0.0, sd, shape[:-1])
    return lfilter([1.0], [1.0, -rho], e, axis=-1)


def _z(x: np.ndarray) -> np.ndarray:
    s = np.nanstd(x, ddof=1)
    return (x - np.nanmean(x)) / s if s > 0 else np.full_like(x, np.nan)


def slot_dummies_frame(df: pd.DataFrame) -> None:
    """The 11 slot-of-day dummies (reference slot 0, 1.7) from the world's 2 h grid (``slot % 12``): world 3b's model sees them (1.8.1)."""
    sod = df["slot"].to_numpy(int) % 12
    for s_ in range(1, 12):
        df[f"sd{s_}"] = (sod == s_).astype(float)


def _finish(rows: dict, test: str) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df["t_row"] = T0 + df["slot"].to_numpy(float) * SLOT_S
    df["day"] = (df["slot"].to_numpy(int) // 12).astype(str)
    df["block2"] = (df["slot"].to_numpy(int) // 24).astype(int)
    df["market_id"], df["event_id"] = df["market_id"].astype(str), df["event_id"].astype(str)
    df["skey"], df["in_scope"], df["ladder"] = "x", 1, 0
    df["f_end_ok"] = 1.0
    return df.reset_index(drop=True)


# --- CH234 worlds (1-4, 12) -------------------------------------------------------------------------------------------------------------------


MQ_LOADING = 0.3  # 1.8.1 worlds 12-14: loading 0.3 per SD of the drift on the lead state and on the twin
MQ_SD = 0.5  # 1.8.1 worlds 12-14: the drift's stationary SD (0.5c a slot)
MQ_RHO = 0.99
Q_FLOOR = 0.15  # 1.8.1 world 3: the census vnum_unknown share, floor 0.15 (a declared convention)
DEV_Q = 0.20  # development / timing runs only, while census_fixed.CH234.q_unknown is unfilled (labelled in the output; never the registered run)


def reflect(u: np.ndarray, lo: float, hi: float) -> np.ndarray:
    """Reflect a path into [lo, hi] (triangle wave; LT10's ``reflect``): world 6's 'reflected AR(0.8)' longshot spreads."""
    w = (u - lo) / (hi - lo)
    return lo + (hi - lo) * np.abs(((w + 1.0) % 2.0) - 1.0)


def _mq_load(x: np.ndarray, mu: np.ndarray, ref: np.ndarray | None = None) -> np.ndarray:
    """1.8.1 worlds 12-14: add ``0.3 x SD(state) x mu / SD(mu)`` (loading 0.3 per SD of the drift, in units of the state's own SD)."""
    r = x if ref is None else ref
    s = float(np.nanstd(r[np.isfinite(r)], ddof=1)) if np.isfinite(r).sum() > 1 else 1.0
    return x + MQ_LOADING * (s if s > 0 else 1.0) * np.asarray(mu, float) / MQ_SD


def _std_on(ref: np.ndarray) -> tuple[float, float]:
    """(mean, SD) over the finite values of ``ref`` (the traded units: the census's centre / scale rule, 2.4)."""
    v = ref[np.isfinite(ref)]
    s = float(v.std(ddof=1)) if len(v) > 1 else float("nan")
    return float(v.mean()) if len(v) else float("nan"), s


def world_ch234(world: str, rng: np.random.Generator, *, markets: int = 400, effect: float = 0.0, q: float | None = None) -> pd.DataFrame:
    """Worlds 1, 2, 3, 3b, 4 and 12 (1.8.1): 400 markets in events of 3, ``n_m`` uniform on 120..252; a logit random walk (step SD 0.25), mids rounded to 0.01,
    movers ``|d| >= 0.01``. The state is the declared one (2.4): ``w = 0.5 + sign(d) x (p_{k-1} - 0.5)``, ``|d|`` winsorised at 0.20, ``xw = z(w) x z(|d|)`` on the
    traded units' centres and scales (the census rule); the twin the same over (k + 2, k + 3] (``w = 0.5`` where that move is 0). ``volume_num`` classes follow
    2.3: a mover at k is unknown if ``volume_num`` is missing at k OR at k - 1. ``q`` (worlds 3, 3b) is ``census_fixed.CH234.q_unknown`` (floor 0.15); None
    refuses. ``effect`` plants a power-run effect of ``effect`` cents per tercile gap of ``xw`` on the traded units (1.8, non-binding). Latent columns
    (``lat_*``) are written for the shape tests only; no model reads them."""
    if world in ("3", "3b"):
        if q is None or not (isinstance(q, (int, float)) and math.isfinite(float(q))):
            raise Refused(f"world {world} needs q = census_fixed.CH234.q_unknown (the census vnum_unknown share); it is unfilled: refused")
        q = max(Q_FLOOR, float(q))
    n_max = 252
    n_m = rng.integers(120, 253, markets)
    sd_step = np.full((markets, n_max), 0.25)
    vol = None
    if world == "4":
        vol = np.exp(ar1(rng, (markets, n_max), 0.9, 0.5))  # log-volatility AR(1) rho 0.9, stationary SD 0.5
        sd_step = 0.25 * vol
    lg = np.empty((markets, n_max))
    lg[:, 0] = rng.normal(0.0, 1.0, markets)
    p = np.empty((markets, n_max))
    p[:, 0] = np.clip(np.round(expit(lg[:, 0]), 2), 0.01, 0.99)
    steps = rng.normal(0.0, 1.0, (markets, n_max)) * sd_step
    drift = world in ("1", "3", "3b", "4", "12")  # world 2 = world 1 without drift
    for t in range(1, n_max):
        g = np.where(p[:, t - 1] < 0.15, -0.003, np.where(p[:, t - 1] > 0.85, 0.002, 0.0)) if drift else 0.0
        pp = expit(lg[:, t - 1])
        lg[:, t] = lg[:, t - 1] + steps[:, t] + g / np.maximum(pp * (1 - pp), 0.02)
        p[:, t] = np.clip(np.round(expit(lg[:, t]), 2), 0.01, 0.99)
    spread = np.maximum(1.0, np.round(2.0 + ar1(rng, (markets, n_max), 0.8, 1.0)))
    a = ar1(rng, (markets, n_max), 0.9, 1.0) if world in ("3", "3b") else np.zeros((markets, n_max))  # world 3 and 3b (= world 3 + A_t)
    A_t = ar1(rng, (1, n_max), 0.9, 1.0) if world == "3b" else np.zeros((1, n_max))
    mu = ar1(rng, (markets, n_max), MQ_RHO, MQ_SD) if world == "12" else np.zeros((markets, n_max))
    ptr = expit(-0.6 + 0.8 * a) if world in ("3", "3b") else np.full((markets, n_max), 0.35)
    traded = rng.random((markets, n_max)) < ptr
    if world == "3":  # row-level: missing with probability logistic(logit(q) - 0.8 a)
        missing = rng.random((markets, n_max)) < expit(logit(q) - 0.8 * a)
    elif world == "3b":  # capture-level: every row of capture t together, probability logistic(logit(q) - 0.8 A_t)
        cap_miss = rng.random(n_max) < expit(logit(q) - 0.8 * A_t[0])
        missing = np.broadcast_to(cap_miss[None, :], (markets, n_max)).copy()
    else:
        missing = np.zeros((markets, n_max), bool)
    d = np.diff(p, axis=1, prepend=p[:, :1])
    cols = ("market_id", "event_id", "slot", "sgn", "d", "absd", "w", "p_k", "spread_k_c", "log1p_vol", "vclass", "y", "w_tw", "absd_tw", "log_rv24s", "lat_a", "lat_A", "lat_mu_k",
            "lat_mu_tw")
    rows: dict[str, list] = {k: [] for k in cols}
    for m in range(markets):
        n = int(n_m[m])
        k = np.arange(13, n - 4)
        if len(k) == 0:
            continue
        dk = d[m, k]
        mov = np.abs(dk) >= 0.01 - 1e-9
        k, dk = k[mov], dk[mov]
        if len(k) == 0:
            continue
        sgn = np.sign(dk)
        pk1 = p[m, k - 1]
        w = 0.5 + sgn * (pk1 - 0.5)  # 2.4: the collateral weight of the side whose buying moved the price
        y = sgn * (p[m, k + 1] - p[m, k]) * 100.0
        if world == "2":
            y = y + 0.15 * np.abs(dk) * 100.0 - 0.1 * spread[m, k]
        if world in ("3", "3b"):
            y = y + 0.3 * a[m, k]
        if world == "3b":
            y = y + 0.3 * A_t[0, k]
        if world == "4":
            y = y + 0.1 * sgn * vol[m, k]
        if world == "12":
            y = y + mu[m, k + 1]  # the drift enters the target (cents a slot)
        rv = np.array([np.log(np.nanstd(np.abs(d[m, kk - 11:kk + 1])) + 0.002) for kk in k])
        lv = (a[m, k] + A_t[0, k] if world in ("3", "3b") else np.zeros(len(k))) + rng.normal(0.0, 0.7, len(k))
        dtw = p[m, k + 3] - p[m, k + 2]
        wtw = 0.5 + np.sign(dtw) * (p[m, k + 2] - 0.5)  # 1.9: w = 0.5 where the twin move is 0 (sign 0)
        unk = missing[m, k] | missing[m, k - 1]  # 2.3: v_k or v_{k-1} missing -> unknown
        vc = np.where(unk, "unknown", np.where(traded[m, k], "traded", "quote_only"))
        for key, val in (("market_id", np.full(len(k), m)), ("event_id", np.full(len(k), m // 3)), ("slot", k), ("sgn", sgn), ("d", dk), ("absd", np.minimum(np.abs(dk), lt.WINSOR_ABSD)),
                         ("w", w), ("p_k", pk1), ("spread_k_c", spread[m, k]), ("log1p_vol", lv), ("vclass", vc), ("y", y), ("w_tw", wtw),
                         ("absd_tw", np.minimum(np.abs(dtw), lt.WINSOR_ABSD)), ("log_rv24s", rv), ("lat_a", a[m, k]), ("lat_A", A_t[0, k]), ("lat_mu_k", mu[m, k]),
                         ("lat_mu_tw", mu[m, k + 3])):
            rows[key].append(val)
    R = {k_: np.concatenate(v) for k_, v in rows.items()}
    df = _finish(R, "CH234")
    pk1 = df["p_k"].to_numpy(float)
    b_ = np.digitize(pk1, [0.15, 0.5, 0.85])
    for i, cen in enumerate(lt.BIN_CENTRES):
        df[f"sb{i}"] = np.where(b_ == i, df["sgn"], 0.0)
        df[f"sb{i}_lvl"] = df[f"sb{i}"] * (pk1 - cen)
    tr = (df["vclass"] == "traded").to_numpy()
    wv, av = df["w"].to_numpy(float), df["absd"].to_numpy(float)
    cf = dict(zip(("w_centre", "w_scale"), _std_on(wv[tr]), strict=True)) | dict(zip(("absd_centre", "absd_scale"), _std_on(av[tr]), strict=True))
    df["xw"] = lt.xw_term(wv, av, cf)
    df["xw_tw"] = lt.xw_term(df["w_tw"].to_numpy(float), df["absd_tw"].to_numpy(float), cf)
    if world == "12":  # loading 0.3 per SD of the drift on the lead product and on the twin product alike
        ref = df["xw"].to_numpy(float)[tr]
        df["xw"] = _mq_load(df["xw"].to_numpy(float), df["lat_mu_k"].to_numpy(float), ref)
        df["xw_tw"] = _mq_load(df["xw_tw"].to_numpy(float), df["lat_mu_tw"].to_numpy(float), ref)
    df["log_rv24s"] = _z(df["log_rv24s"].to_numpy(float))
    df["traded"] = tr.astype(float)
    df["n_members"] = 3.0
    slot_dummies_frame(df)
    if effect:
        gap = b.terciles(df["xw"].to_numpy(float)[tr])[2]
        df["y"] = df["y"] + np.where(tr, effect * df["xw"].to_numpy(float) / gap, 0.0)
    return df


# --- CH233 worlds (5-8, 13) -------------------------------------------------------------------------------------------------------------------


def world_ch233(world: str, rng: np.random.Generator, *, events: int = 200, effect: float = 0.0) -> pd.DataFrame:
    """Worlds 5-8 and 13 (1.8.1): 200 events of 3-10 members, ``n`` uniform on 120..252 captures; member bids ``b_j + e_t + u_{j,t}`` (``e_t ~ N(0, 1.5c^2)``
    iid); spreads ``max(1, round(2 + 1.5|e_t| + AR(0.7)))`` in the same slot; target the member's next spread change; 10% of member units removed at random
    in worlds 5-8. World 6: the favourite carries every move, the longshots' spreads a reflected AR(0.8) around 3c. World 8: the siblings' bid-change
    VARIANCE scaled by ``exp(0.5 L_e)`` (SD by ``exp(0.25 L_e)``). World 13: a drift ``mu_t`` AR(1) rho 0.99 (SD 0.5c) entering the target and, with loading
    0.3 per SD, ``cl_sib`` and its twin. ``effect`` = cents per tercile gap of ``z cl_sib`` (power run)."""
    cols = ("market_id", "event_id", "slot", "cl_sib", "ca_sib", "cl_tw", "spread_k_c", "own_dspread_c", "own_dbid_c", "n_elig", "y", "ctrl_liq", "lat_mu_k", "lat_mu_tw", "lat_Le")
    rows: dict[str, list] = {k: [] for k in cols}
    for e in range(events):
        M = int(rng.integers(3, 11))
        n = int(rng.integers(120, 253))
        eshock = rng.normal(0.0, 1.5, n)
        mu = ar1(rng, (1, n), MQ_RHO, MQ_SD)[0] if world == "13" else np.zeros(n)
        bid = rng.uniform(5.0, 60.0, (M, 1)) + np.zeros((M, n))
        L = rng.normal(0.0, 1.0, M)
        Le = float(L.mean())
        u = rng.normal(0.0, 0.5, (M, n))
        if world == "6":
            fav = np.zeros((M, 1))
            fav[0] = 1.0
            common = fav * eshock[None, :]
            u = fav * u + (1 - fav) * rng.normal(0.0, 0.2, (M, n))  # the longshots static up to noise
        else:
            common = np.broadcast_to(eshock[None, :], (M, n))
        if world == "8":  # the siblings' bid-change variance scaled by exp(0.5 L_e): the SD by exp(0.25 L_e)
            sc8 = math.exp(0.25 * Le)
            common, u = common * sc8, u * sc8
        f = ar1(rng, (1, n), 0.8, 1.0)[0] if world == "7" else np.zeros(n)
        eta = f - 0.8 * np.concatenate([[0.0], f[:-1]])  # f's innovation
        bb = bid + common + u - (0.5 * eta[None, :] if world == "7" else 0.0)
        rho = (0.9 - 0.3 * ndtr(L))[:, None] if world == "8" else np.full((M, 1), 0.7)
        noise = np.stack([ar1(rng, (1, n), float(rho[j, 0]), 1.0)[0] for j in range(M)])
        shock = np.abs(common[0]) if world != "6" else np.abs(eshock)
        if world == "6":
            ls = reflect(3.0 + ar1(rng, (M, n), 0.8, 1.0), 1.0, 40.0)  # longshot spreads: reflected AR(0.8) around 3c
            s = np.where(np.arange(M)[:, None] == 0, 2.0 + 1.5 * shock[None, :] + noise, ls)
        else:
            s = 2.0 + 1.5 * shock[None, :] + noise
        s = np.maximum(1.0, np.round(s + (f[None, :] if world == "7" else 0.0)))
        db = np.diff(bb, axis=1, prepend=bb[:, :1])
        da = np.diff(bb + s, axis=1, prepend=(bb + s)[:, :1])
        cl = db.sum(axis=0)[None, :] - db
        ca = da.sum(axis=0)[None, :] - da
        ds = np.diff(s, axis=1, prepend=s[:, :1])
        k = np.arange(2, n - 4)
        for j in range(M):
            y = s[j, k + 1] - s[j, k] + (mu[k + 1] if world == "13" else 0.0)
            for key, val in (("market_id", np.full(len(k), f"{e}-{j}")), ("event_id", np.full(len(k), e)), ("slot", k), ("cl_sib", cl[j, k]), ("ca_sib", ca[j, k]),
                             ("cl_tw", cl[j, k + 3]), ("spread_k_c", s[j, k]), ("own_dspread_c", ds[j, k]), ("own_dbid_c", db[j, k]), ("n_elig", np.full(len(k), float(M))), ("y", y),
                             ("ctrl_liq", np.full(len(k), L[j]) + rng.normal(0.0, 0.5, len(k))), ("lat_mu_k", mu[k]), ("lat_mu_tw", mu[k + 3]), ("lat_Le", np.full(len(k), Le))):
                rows[key].append(val)
    R = {k_: np.concatenate(v) for k_, v in rows.items()}
    df = _finish(R, "CH233")
    if world in ("5", "6", "7", "8"):
        df = df[rng.random(len(df)) >= 0.10].reset_index(drop=True)
    if world == "13":  # loading 0.3 per SD of the drift on the lead state and the twin alike
        ref = df["cl_sib"].to_numpy(float)
        df["cl_sib"] = _mq_load(ref, df["lat_mu_k"].to_numpy(float))
        df["cl_tw"] = _mq_load(df["cl_tw"].to_numpy(float), df["lat_mu_tw"].to_numpy(float), ref)
    sc = float(np.nanstd(df["cl_sib"].to_numpy(float), ddof=1)) or 1.0
    df["zcl"] = df["cl_sib"] / sc
    df["zca"] = df["ca_sib"] / (float(np.nanstd(df["ca_sib"].to_numpy(float), ddof=1)) or 1.0)
    df["zcl_tw"] = df["cl_tw"] / sc
    df["arm"] = "primary"
    if world == "8":
        df["liq_proxy"] = df["ctrl_liq"]
    if effect:
        gap = b.terciles(df["zcl"].to_numpy(float))[2]
        df["y"] = df["y"] + effect * df["zcl"] / gap
    return df


# --- CH232 worlds (9-11, 14, 15) --------------------------------------------------------------------------------------------------------------


def world_ch232(world: str, rng: np.random.Generator, *, per_panel: int = 160, effect: float = 0.0) -> pd.DataFrame:
    """Worlds 9, 10, 11, 14 and 15 (1.8.1): 160 rewarded and 160 control markets, ``n_m`` uniform on 120..252, a bounded logit walk (step SD 0.3) started
    uniformly in [0.06, 0.94]; the unit population by 4.2's rules (approach zone, movers, first crossing of the UTC day, tick-coincident exclusion). World 14:
    a drift ``mu`` AR(1) rho 0.99 (SD 0.5c) on reward-panel markets entering the target and, with loading 0.3 per SD, the crossing propensity: an outward
    logit drift of 0.3 x the step SD per SD of ``mu`` (toward the nearer boundary), at the lead and the twin alike. ``effect`` = cents between classes."""
    mk = 2 * per_panel
    n_max = 252
    rew = np.r_[np.ones(per_panel), np.zeros(per_panel)]
    n_m = rng.integers(120, 253, mk)
    mu = ar1(rng, (mk, n_max), MQ_RHO, MQ_SD) * rew[:, None] if world == "14" else np.zeros((mk, n_max))
    lg = np.empty((mk, n_max))
    lg[:, 0] = logit(rng.uniform(0.06, 0.94, mk))
    st = rng.normal(0.0, 0.3, (mk, n_max))
    for t in range(1, n_max):
        out_drift = MQ_LOADING * 0.3 * mu[:, t] / MQ_SD * np.sign(lg[:, t - 1]) if world == "14" else 0.0
        lg[:, t] = np.clip(lg[:, t - 1] + st[:, t] + out_drift, logit(0.02), logit(0.98))
    f = expit(lg)
    noise = ar1(rng, (mk, n_max), 0.8, 1.0)
    if world == "15":
        h = np.maximum(0.005, 0.015 + ar1(rng, (mk, n_max), 0.8, 0.01))
        bid = np.clip(np.floor((f - h) / 0.01) * 0.01, 0.01, 0.99)
        ask = np.clip(np.ceil((f + h) / 0.01) * 0.01, 0.01, 0.99)
        ask = np.maximum(ask, bid + 0.01)
        mid = (bid + ask) / 2.0
        spread = (ask - bid) * 100.0
    else:
        mid = np.clip(np.round(f / 0.005) * 0.005, 0.01, 0.99)
        d_all = np.abs(np.diff(mid, axis=1, prepend=mid[:, :1]))
        if world == "10":
            base = 2.0 + 4.0 * np.where(mid < 0.5, np.exp(-(mid - 0.04) / 0.03), np.exp(-((1 - mid) - 0.04) / 0.03))
        else:
            base = 2.0 + 3.0 * d_all * 100.0 * 0.2
        spread = np.maximum(1.0, np.round(base + noise))
        if world == "11":
            for m in range(mk):
                cross = ((mid[m, 1:] < 0.04) ^ (mid[m, :-1] < 0.04)) | ((mid[m, 1:] > 0.96) ^ (mid[m, :-1] > 0.96))
                for t in np.flatnonzero(cross) + 1:
                    spread[m, t:t + 3] += 1.0
    tick_rec = np.zeros((mk, n_max), bool)
    if world == "11":
        cross = np.zeros((mk, n_max), bool)
        cross[:, 1:] = ((mid[:, 1:] < 0.04) ^ (mid[:, :-1] < 0.04)) | ((mid[:, 1:] > 0.96) ^ (mid[:, :-1] > 0.96))
        tick_rec = cross & (rng.random((mk, n_max)) < 0.70)
    rows: dict[str, list] = {k: [] for k in ("market_id", "event_id", "slot", "rew", "d", "absd", "d_tow", "dist", "upper", "spread_k_c", "dspread_c", "xo", "xr", "y", "xo_tw", "dS_ticks",
                                              "S_ticks", "lat_mu_k")}
    for m in range(mk):
        n = int(n_m[m])
        k = np.arange(13, n - 4)
        mp, mc = mid[m, k - 1], mid[m, k]
        zone_lo = (mp >= 0.10 - 1e-9) & (mp <= 0.14 + 1e-9)
        zone_hi = (mp >= 0.86 - 1e-9) & (mp <= 0.90 + 1e-9)
        zone = zone_lo | zone_hi
        dk = mc - mp
        keep = zone & (np.abs(dk) >= 0.01 - 1e-9) & ~((mc < 0.04) | (mc > 0.96)) & ~tick_rec[m, k]
        out_cross = ((mp >= 0.10 - 1e-9) & (mp <= 0.90 + 1e-9)) & ((mc < 0.10 - 1e-9) | (mc > 0.90 + 1e-9))
        prev = np.zeros(len(k), bool)
        seen_day: dict[int, bool] = {}
        for i, kk in enumerate(k):
            day = int(kk) // 12
            if int(kk) % 12 == 0:
                seen_day[day] = False
            prev[i] = seen_day.get(day, False)
            if out_cross[i]:
                seen_day[day] = True
        idx = np.flatnonzero(keep)
        if len(idx) == 0:
            continue
        kk = k[idx]
        xo = (out_cross & ~prev)[idx].astype(float)
        xr = (out_cross & prev)[idx].astype(float)
        upper = zone_hi[idx].astype(float)
        d_tow = np.where(upper == 1, dk[idx], -dk[idx])
        dist = np.where(upper == 1, 0.90 - mp[idx], mp[idx] - 0.10)
        y = spread[m, kk + 1] - spread[m, kk] + effect * xo * (rew[m]) + (mu[m, kk] if world == "14" else 0.0)
        tw_in = (mid[m, kk + 2] >= 0.10 - 1e-9) & (mid[m, kk + 2] <= 0.90 + 1e-9) & ((mid[m, kk + 3] < 0.10 - 1e-9) | (mid[m, kk + 3] > 0.90 + 1e-9))
        for key, val in (("market_id", np.full(len(idx), m)), ("event_id", np.full(len(idx), m // 3)), ("slot", kk), ("rew", np.full(len(idx), rew[m])), ("d", dk[idx]), ("absd", np.abs(dk[idx])),
                         ("d_tow", d_tow), ("dist", dist), ("upper", upper), ("spread_k_c", spread[m, kk]), ("dspread_c", spread[m, kk] - spread[m, kk - 1]), ("xo", xo), ("xr", xr),
                         ("y", y), ("xo_tw", tw_in.astype(float)), ("dS_ticks", np.round(spread[m, kk] - spread[m, kk - 1])), ("S_ticks", np.round(spread[m, kk])), ("lat_mu_k", mu[m, kk])):
            rows[key].append(val)
    R = {k_: np.concatenate(v) if v else np.array([]) for k_, v in rows.items()}
    df = _finish(R, "CH232")
    S, dS = df["S_ticks"].to_numpy(float), df["dS_ticks"].to_numpy(float)
    df["S2"], df["S3"], df["S4p"] = (S == 2).astype(float), (S == 3).astype(float), (S >= 4).astype(float)
    df["dSm2p"], df["dSm1"], df["dSp1"], df["dSp2p"] = (dS <= -2).astype(float), (dS == -1).astype(float), (dS == 1).astype(float), (dS >= 2).astype(float)
    df["arm"] = "out"
    return df.drop(columns=["S_ticks", "dS_ticks"])


# --- evaluation -------------------------------------------------------------------------------------------------------------------------------


GENERATORS = {**{w: ("CH234", w) for w in ("1", "2", "3", "3b", "4", "12")}, **{w: ("CH233", w) for w in ("5", "6", "7", "8", "13")}, **{w: ("CH232", w) for w in ("9", "10", "11", "14", "15")}}
CTRL = {
    "CH234": ["absd", "sb0", "sb1", "sb2", "sb3", "sb0_lvl", "sb1_lvl", "sb2_lvl", "sb3_lvl", "spread_k_c", "log1p_vol", "log_rv24s", "w"],
    "CH233": ["spread_k_c", "own_dspread_c", "own_dbid_c", "n_elig"],
    "CH232": ["xr", "d_tow", "absd", "dist", "upper", "spread_k_c", "dspread_c", "S2", "S3", "S4p", "dSm2p", "dSm1", "dSp1", "dSp2p"],
}
SLOT_DUMMIES = tuple(f"sd{s_}" for s_ in range(1, 12))
EXTRA_CTRL = {"3b": SLOT_DUMMIES, "8": ("liq_proxy",)}  # 1.8.1: world 3b's model sees the slot-of-day dummies; world 8's the noisy liquidity proxy
Q_WORLDS = ("3", "3b")


def generate(world: str, rng: np.random.Generator, *, effect: float = 0.0, small: bool = False, q: float | None = None) -> tuple[pd.DataFrame, str]:
    test, w = GENERATORS[world]
    kw: dict = {"effect": effect}
    if small:
        kw.update({"CH234": {"markets": 60}, "CH233": {"events": 25}, "CH232": {"per_panel": 60}}[test])
    if test == "CH234":
        kw["q"] = q
    return {"CH234": world_ch234, "CH233": world_ch233, "CH232": world_ch232}[test](w, rng, **kw), test


def _controls(test: str, world: str, df: pd.DataFrame) -> list[str]:
    c = [x for x in CTRL[test] if x in df]
    c += [x for x in EXTRA_CTRL.get(world, ()) if x in df and x not in c]
    return c


def census_fixed_error(spec: dict, tests) -> str | None:
    """The registered size check needs every census-fixed value of every surviving test filled (7, 8.4 step 5): a missing block, a None or a non-finite value
    anywhere in it (nested dicts and lists included) refuses. ``exclude_family`` is ``""`` when the census excluded no family (never None once filled)."""
    cf = spec.get("census_fixed") or {}

    def bad(v) -> bool:
        if v is None:
            return True
        if isinstance(v, dict):
            return not v or any(bad(x) for x in v.values())
        if isinstance(v, (list, tuple)):
            return not v or any(bad(x) for x in v)
        if isinstance(v, float):
            return not math.isfinite(v)
        return False

    for t in tests:
        blk = cf.get(t)
        if not isinstance(blk, dict) or not blk:
            return f"census_fixed.{t} is not filled"
        miss = sorted(k for k, v in blk.items() if bad(v))
        if miss:
            return f"census_fixed.{t} has unfilled values {miss}"
    return None


def world_q(spec: dict, *, dev: bool) -> tuple[float | None, str]:
    """World 3 / 3b's ``q`` (1.8.1): ``census_fixed.CH234.q_unknown`` (floor 0.15). A registered run refuses while it is unfilled; a development or timing run
    uses the labelled placeholder 0.20 (no result of such a run is ever a size result)."""
    q = ((spec.get("census_fixed") or {}).get("CH234") or {}).get("q_unknown")
    if q is not None and isinstance(q, (int, float)) and math.isfinite(float(q)):
        return max(Q_FLOOR, float(q)), "census_fixed.CH234.q_unknown"
    if not dev:
        raise Refused("census_fixed.CH234.q_unknown is unfilled: worlds 3 / 3b refuse (1.8.1)")
    return DEV_Q, "development placeholder 0.20 (census_fixed.CH234.q_unknown unfilled; not a size result)"


def evaluate_world(world: str, sub_seed: int, spec: dict, *, stat: str, draws: int, effect: float = 0.0, small: bool = False, q: float | None = None) -> dict:
    """One world under its binding test: the gate rejection (the analysis' own gate path) or the verdict-size statistic (analytic p < 0.05 and F and the point
    condition hold; the gate is omitted). ``q`` is world 3 / 3b's census unknown share (refused there when None)."""
    rng = np.random.default_rng(sub_seed)
    df, test = generate(world, rng, effect=effect, small=small, q=q)
    term = lt.TERM[test]
    ctrl_all = _controls(test, world, df)
    rec: dict = {"n": len(df)}
    X = df
    if test == "CH232":
        P = df[df["rew"] == 1].reset_index(drop=True)
        P, _ = lt.fix_panels11(P) if "rew" in P and len(P) else (P, {})
    elif test == "CH234":
        P = df[(df["vclass"] == "traded")].reset_index(drop=True)
    else:
        P = df
    ctrl = [c for c in ctrl_all if c in P and np.nanstd(P[c].to_numpy(float)) > 0]
    y = P["y"].to_numpy(float)
    seed = int(sub_seed % (2**31 - 1))
    if stat == "gate":
        if test == "CH233":
            g = an.event_index_fl_gate(P, y, term, ctrl, draws=draws, seed=seed, sign=+1, min_rows=16)
        else:
            g = b.block_fl_gate(P, y, term, ctrl, sign=+1, draws=draws, seed=seed, min_n=16, group="market_id", order="t_row")
        rec.update(gate_testable=bool(g.get("testable")), reject=bool(g.get("passes")))
        return rec
    r = an.fit11(P, y, term, ctrl, seed=seed, minor=None, n_boot=20)
    if not r.get("testable"):
        return {**rec, "reject": False, "testable": False}
    minor = an.g_minor(P, r["_mask"], test)
    if minor is not None:
        r = an.fit11(P, y, term, ctrl, seed=seed, minor=minor, n_boot=20)
    f = an.f_rule(P, y, test, ctrl, r, spec)
    if test == "CH234":
        Xall = X.assign(rew=np.nan)
    else:
        Xall = X.assign(rew=X["rew"]) if "rew" in X else X
    pc = {"holds": False}
    try:
        pc = an.point_condition(Xall, test, ctrl, r, spec, Xall["y"].to_numpy(float), seed)
    except (KeyError, ValueError):
        pass
    cond = bool(f.get("available") and f.get("holds") and pc.get("holds"))
    rec.update(p_analytic=float(r["p"]), analytic_reject=bool(r["p"] < 0.05), reject=bool(r["p"] < 0.05 and cond), f_holds=bool(f.get("holds", False)), point_holds=bool(pc.get("holds", False)))
    return rec


def size_check(*, worlds: int, draws: int, seed: int, spec: dict, tests=None, scenarios=SCENARIO_ORDER, power_worlds: int | None = None, small: bool = False,
               registered: bool = False, progress=None, q: float | None = None) -> dict:
    """``worlds`` worlds per scenario (one generator seeded ``seed``; the world sub-seeds are drawn in table order), each under its binding test and statistic
    (1.8). Criterion: the frozen 0.058 at 2,000 worlds (``0.05 + 1.645 sqrt(0.0475 / worlds)`` for development sizes). Non-binding: the power runs (generators
    ``seed x 100 + n``). A failing gate scenario sets only its test to 'SE check failed (size scenario)', a failing verdict-size scenario to '(mechanical
    world)'; k unchanged; no rerun, reseed or redesign. ``q`` = world 3 / 3b's census unknown share (worlds 3 / 3b refuse when None)."""
    if seed == REGISTERED_SEED and not registered:
        raise Refused("seed 20261497 is the registered size check's: development runs use 20261497 x 100 + 99 (1.8: no preliminary run at the registered seed)")
    unknown = [s for s in scenarios if s not in SCENARIOS]
    if unknown:
        raise Refused(f"unknown size scenario {unknown}")
    lim = limit_for(worlds)
    alive = list(tests) if tests is not None else list(TESTS)
    master = np.random.default_rng(seed)
    res: dict = {t: {} for t in alive}
    for sc in scenarios:
        sp = SCENARIOS[sc]
        if sp["test"] not in alive:
            continue
        k = n = 0
        for i in range(worlds):
            sub = int(master.integers(1, 2**62))
            r = evaluate_world(sc, sub, spec, stat=sp["stat"], draws=draws, small=small, q=q)
            n += 1
            k += int(r.get("reject", False))
            if progress:
                progress(sc, i + 1, worlds)
        rate = k / n if n else float("nan")
        res[sp["test"]][sc] = {"scenario": sc, "stat": sp["stat"], "worlds": n, "rejections": k, "rate": rate, "limit": lim, "ok": bool(n == worlds and rate <= lim)}
    per_test = {}
    for t in alive:
        fs, fm, miss = [], [], []
        for sc in (SCENARIO_ORDER if registered else scenarios):
            if SCENARIOS[sc]["test"] != t:
                continue
            r = res[t].get(sc)
            if r is None or r["worlds"] != worlds:
                miss.append(sc)
            elif not r["ok"]:
                (fs if SCENARIOS[sc]["stat"] == "gate" else fm).append(sc)
        per_test[t] = {"status": "fail_size_scenario" if (fs or miss) else ("fail_mechanical_world" if fm else "pass"), "failed_size": fs, "failed_mechanical": fm, "missing": miss}
    out = {"worlds": worlds, "draws": draws, "seed": seed, "limit": lim, "scenarios": res, "per_test": per_test, "seed_kind": "registered" if registered else "development"}
    if power_worlds:
        out["power_runs"] = {}
        for t in alive:
            label, slope, n_ = POWER[t]
            g = np.random.default_rng(seed * 100 + n_)
            first = {"CH234": "1", "CH233": "5", "CH232": "9"}[t]
            hit = sum(int(evaluate_world(first, int(g.integers(1, 2**62)), spec, stat="gate", draws=draws, effect=slope, small=small).get("reject", False)) for _ in range(power_worlds))
            out["power_runs"][t] = {"effect": label, "worlds": power_worlds, "gate_power": hit / power_worlds, "binding": False}
    return out


# --- size-check timing (8.4 step 3, R1 should-fix 9): the clock only ------------------------------------------------------------------------------


POWER_RUN_SEEDS = tuple(REGISTERED_SEED * 100 + k for k in (41, 42, 43))  # the 3 x 500 power-run generators (review 2026-10-23 defect 4)
TIMING_SEED = REGISTERED_SEED * 100 + 98  # neither the registered seed nor the development seed (8.4 step 3: "a timing seed other than 20261497")
TIMING_KEYS = frozenset({"purpose", "seed", "seed_kind", "worlds_per_scenario", "draws", "seconds_per_world", "seconds_total", "projection", "q_source", "code_sha256", "spec_sha256",
                         "design_text_sha256", "host", "started_utc", "finished_utc"})


def size_timing(*, spec: dict, worlds: int = 20, draws: int = 200, seed: int = TIMING_SEED, small: bool = False, clock=None) -> dict:
    """8.4 step 3: the wall-clock seconds per world of each of the 16 scenarios at a timing seed (never 20261497, never the development seed), projected to
    2,000 worlds x 200 draws (plus the 3 x 500 power-run worlds on worlds 1, 5, 9). ONLY the clock is kept: each world's return value is dropped unread, and
    the output holds no rejection, rate, p-value, status or any other result of the worlds."""
    import time as _time

    if seed in (REGISTERED_SEED, DEV_SEED) or seed in POWER_RUN_SEEDS:
        raise Refused("the timing run needs a seed other than 20261497, the development seed and the power-run generators 20261497*100+41/42/43 (8.4 step 3)")
    if worlds < 1 or draws < 1:
        raise Refused("worlds / draws too small")
    clock = clock or _time.perf_counter
    q, q_src = world_q(spec, dev=True)
    master = np.random.default_rng(seed)
    per: dict[str, float] = {}
    for sc in SCENARIO_ORDER:
        stat = SCENARIOS[sc]["stat"]
        t0 = clock()
        for _ in range(worlds):
            evaluate_world(sc, int(master.integers(1, 2**62)), spec, stat=stat, draws=draws, small=small, q=q)  # return value deliberately discarded (clock only)
        per[sc] = (clock() - t0) / worlds
    sc_cfg = spec["size_check"]
    W_reg, D_reg, PW = int(sc_cfg["worlds"]), int(sc_cfg["draws"]), int(sc_cfg["power_worlds"])
    f_draw = D_reg / draws
    proj_sc = {sc: per[sc] * W_reg * f_draw for sc in SCENARIO_ORDER}
    proj_pw = sum(per[w] * PW * f_draw for w in ("1", "5", "9"))
    total_s = sum(proj_sc.values()) + proj_pw
    census = lt.epoch("2026-11-09T00:00:00Z")  # 8.4 step 3: the planned census commit
    end = census + total_s + 24 * 3600.0
    lim = lt.epoch("2026-11-15T00:00:00Z")
    out = {"purpose": "LT11 size-check timing (LIVE_TESTS_11.md 8.4 step 3): wall-clock only; no result of these worlds is recorded", "seed": seed, "seed_kind": "timing",
           "worlds_per_scenario": worlds, "draws": draws, "seconds_per_world": per, "seconds_total": float(sum(per.values()) * worlds), "q_source": q_src,
           "projection": {"worlds": W_reg, "draws": D_reg, "power_worlds": PW, "draw_scaling": "linear in draws", "seconds_by_scenario": proj_sc, "power_run_seconds": proj_pw,
                          "total_seconds": total_s, "total_hours": total_s / 3600.0, "planned_census_commit_utc": "2026-11-09T00:00:00Z", "margin_h": 24,
                          "projected_end_utc": lt.iso(end), "fast_lane_limit_utc": "2026-11-15T00:00:00Z", "ordered_lane_ledger_line_needed": bool(end > lim)}}
    return out


def size_timing_cli(args, write_out) -> int:
    try:
        spec = lt.load_spec(sha=None)
    except RuntimeError as exc:
        print(f"refusing: {exc}")
        return 2
    if (e := lt.design_text_error()) is not None:
        print(f"refusing: {e['error']}")
        return 2
    import platform
    import time as _time

    started = lt.iso(_time.time())
    try:
        out = size_timing(spec=spec, worlds=int(args.worlds), draws=int(args.draws), seed=int(args.seed))
    except Refused as exc:
        print(f"refusing: {exc}")
        return 2
    out.update(code_sha256=lt.code_hashes(), spec_sha256=spec["_sha256"], design_text_sha256=lt.design_text_sha(), host=platform.node(), started_utc=started, finished_utc=lt.iso(_time.time()))
    assert set(out) <= TIMING_KEYS, sorted(set(out) - TIMING_KEYS)
    return write_out(args.out, json.dumps(bd._clean(out), sort_keys=True, indent=1, default=str))


def size_check_cli(args, write_out) -> int:
    try:
        spec = lt.load_spec(sha=None)
    except RuntimeError as exc:
        print(f"refusing: {exc}")
        return 2
    if (e := lt.design_text_error()) is not None:
        print(f"refusing: {e['error']}")
        return 2
    sc = spec["size_check"]
    worlds = args.worlds if args.worlds is not None else int(sc["worlds"])
    draws = args.draws if args.draws is not None else int(sc["draws"])
    if worlds < 2 or draws < 1:
        print("refusing: worlds / draws too small")
        return 2
    tests = spec.get("k_tests")
    if not args.dev:
        if not isinstance(tests, list) or not tests or [t for t in tests if t not in TESTS] or set(tests) & set(spec.get("dropped_tests") or []):
            print("refusing: the registered size check needs k_tests filled with known, undropped tests (census values first)")
            return 2
        if (err := census_fixed_error(spec, tests)) is not None:
            print(f"refusing: {err}")
            return 2
    if int(spec["seeds"]["size_check"]) != REGISTERED_SEED:
        print("refusing: the spec's size-check seed is not 20261497")
        return 2
    try:
        q, q_src = world_q(spec, dev=bool(args.dev)) if (tests is None or "CH234" in tests or args.dev) else (None, "CH234 not in k_tests")
    except Refused as exc:
        print(f"refusing: {exc}")
        return 2
    out = size_check(worlds=worlds, draws=draws, seed=REGISTERED_SEED if not args.dev else DEV_SEED, spec=spec, tests=list(tests) if tests else None, registered=not args.dev,
                     power_worlds=int(sc["power_worlds"]) if not args.dev else int(getattr(args, "power_worlds", 0) or 0), q=q)
    out.update(code_sha256=lt.code_hashes(), spec_sha256=spec["_sha256"], design_text_sha256=lt.design_text_sha(), dev=bool(args.dev), q_source=q_src)
    return write_out(args.out, json.dumps(bd._clean(out), sort_keys=True, indent=1, default=str))
