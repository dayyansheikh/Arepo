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


def limit_for(worlds: int) -> float:
    return 0.05 + 1.645 * math.sqrt(0.0475 / worlds)


def ar1(rng, shape, rho: float, sd: float = 1.0) -> np.ndarray:
    e = rng.normal(0.0, sd * math.sqrt(1.0 - rho**2), shape)
    e[..., 0] = rng.normal(0.0, sd, shape[:-1])
    return lfilter([1.0], [1.0, -rho], e, axis=-1)


def _z(x: np.ndarray) -> np.ndarray:
    s = np.nanstd(x, ddof=1)
    return (x - np.nanmean(x)) / s if s > 0 else np.full_like(x, np.nan)


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


def world_ch234(world: str, rng: np.random.Generator, *, markets: int = 400, effect: float = 0.0) -> pd.DataFrame:
    """Worlds 1, 2, 3, 3b, 4 and 12: 400 markets in events of 3, ``n_m`` uniform on 120..252; a logit random walk (step SD 0.25), mids rounded to 0.01, movers
    ``|d| >= 0.01``; world-specific drift / continuation / leak per 1.8.1. ``effect`` plants a power-run effect on the centred product."""
    n_max = 252
    n_m = rng.integers(120, 253, markets)
    sd_step = np.full((markets, n_max), 0.25)
    vol = None
    if world == "4":
        vol = np.exp(ar1(rng, (markets, n_max), 0.9, 0.5))
        sd_step = 0.25 * vol
    lg = np.empty((markets, n_max))
    lg[:, 0] = rng.normal(0.0, 1.0, markets)
    p = np.empty((markets, n_max))
    p[:, 0] = np.clip(np.round(expit(lg[:, 0]), 2), 0.01, 0.99)
    steps = rng.normal(0.0, 1.0, (markets, n_max)) * sd_step
    for t in range(1, n_max):
        g = np.where(p[:, t - 1] < 0.15, -0.003, np.where(p[:, t - 1] > 0.85, 0.002, 0.0)) if world in ("1", "3", "3b", "4", "12") else 0.0
        pp = expit(lg[:, t - 1])
        lg[:, t] = lg[:, t - 1] + steps[:, t] + g / np.maximum(pp * (1 - pp), 0.02)
        p[:, t] = np.clip(np.round(expit(lg[:, t]), 2), 0.01, 0.99)
    spread = np.maximum(1.0, np.round(2.0 + ar1(rng, (markets, n_max), 0.8, 1.0)))
    a = ar1(rng, (markets, n_max), 0.9, 1.0) if world in ("3", "12") else np.zeros((markets, n_max))
    A_t = ar1(rng, (1, n_max), 0.9, 1.0) if world == "3b" else np.zeros((1, n_max))
    mu = ar1(rng, (markets, n_max), 0.99, 1.0) if world == "12" else None
    q = max(0.15, 0.20)  # LT11 ambiguity A11: the census vnum_unknown share (floor 0.15) is not known to the worlds; the 0.20 convention stands in
    # per-slot traded flag and missing-volume flag
    ptr = expit(-0.6 + 0.8 * a) if world in ("3", "3b") else np.full((markets, n_max), 0.35)
    traded = rng.random((markets, n_max)) < ptr
    miss_p = expit(logit(q) - 0.8 * a) if world == "3" else (np.broadcast_to(expit(logit(q) - 0.8 * A_t), (markets, n_max)) if world == "3b" else np.zeros((markets, n_max)))
    missing = rng.random((markets, n_max)) < miss_p
    if world == "3b":
        cap_miss = rng.random(n_max) < expit(logit(q) - 0.8 * A_t[0])
        missing = np.broadcast_to(cap_miss[None, :], (markets, n_max)).copy()
    w_traded = rng.uniform(0.2, 1.0, (markets, n_max))
    w = np.where(traded, w_traded, 0.5)
    if mu is not None:
        w = w * np.exp(0.3 * mu)
    d = np.diff(p, axis=1, prepend=p[:, :1])
    rows: dict[str, list] = {k: [] for k in ("market_id", "event_id", "slot", "sgn", "d", "absd", "w", "p_k", "spread_k_c", "log1p_vol", "vclass", "y", "w_tw", "absd_tw", "log_rv24s", "pk1")}
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
        nxt = p[m, k + 1] - p[m, k]
        y = sgn * nxt * 100.0
        if world == "2":
            y = y + 0.15 * np.abs(dk) * 100.0 - 0.1 * spread[m, k]
        if world in ("3", "12"):
            y = y + 0.3 * a[m, k] + (mu[m, k + 1] * 0.5 if mu is not None else 0.0)
        if world == "3b":
            y = y + 0.3 * A_t[0, k]
        if world == "4":
            y = y + 0.1 * sgn * vol[m, k] * 1.0
        rv = np.array([np.log(np.nanstd(np.abs(d[m, kk - 11:kk + 1])) + 0.002) for kk in k])
        lv = (a[m, k] + A_t[0, k] if world in ("3", "3b") else np.zeros(len(k))) + rng.normal(0.0, 0.7, len(k))
        dtw = p[m, k + 3] - p[m, k + 2]
        wtw = np.where(np.abs(dtw) < 1e-9, 0.5, w[m, k + 2])
        vc = np.where(missing[m, k], "unknown", np.where(traded[m, k], "traded", "quote_only"))
        for key, val in (("market_id", np.full(len(k), m)), ("event_id", np.full(len(k), m // 3)), ("slot", k), ("sgn", sgn), ("d", dk), ("absd", np.abs(dk)), ("w", w[m, k]),
                         ("p_k", p[m, k - 1]), ("spread_k_c", spread[m, k]), ("log1p_vol", lv), ("vclass", vc), ("y", y), ("w_tw", wtw), ("absd_tw", np.abs(dtw)), ("log_rv24s", rv),
                         ("pk1", p[m, k - 1])):
            rows[key].append(val)
    R = {k_: np.concatenate(v) for k_, v in rows.items()}
    pk1 = R.pop("pk1")
    df = _finish(R, "CH234")
    cen = np.array([0.075, 0.325, 0.675, 0.925])
    b_ = np.digitize(pk1, [0.15, 0.5, 0.85])
    for i in range(4):
        df[f"sb{i}"] = np.where(b_ == i, df["sgn"], 0.0)
        df[f"sb{i}_lvl"] = df[f"sb{i}"] * (pk1 - cen[i])
    wa = df["w"].to_numpy(float) * df["absd"].to_numpy(float)
    df["xw"] = _z(df["w"].to_numpy(float)) * _z(df["absd"].to_numpy(float))
    df["xw_tw"] = _z(df["w_tw"].to_numpy(float)) * _z(df["absd_tw"].to_numpy(float))
    df["log_rv24s"] = _z(df["log_rv24s"].to_numpy(float))
    df["traded"] = (df["vclass"] == "traded").astype(float)
    df["n_members"] = 3.0
    if effect:
        df["y"] = df["y"] + effect * df["xw"]
    del wa
    return df


# --- CH233 worlds (5-8, 13) -------------------------------------------------------------------------------------------------------------------


def world_ch233(world: str, rng: np.random.Generator, *, events: int = 200, effect: float = 0.0) -> pd.DataFrame:
    """Worlds 5-8 and 13: 200 events of 3-10 members, ``n`` uniform on 120..252 captures; member bids ``b_j + e_t + u``; spreads ``max(1, round(2 + 1.5|e_t| + AR(0.7)))``
    in the same slot; target the member's next spread change; 10% of member units removed at random in worlds 5-8."""
    rows: dict[str, list] = {k: [] for k in ("market_id", "event_id", "slot", "cl_sib", "ca_sib", "cl_tw", "spread_k_c", "own_dspread_c", "own_dbid_c", "n_elig", "y", "ctrl_liq")}
    for e in range(events):
        M = int(rng.integers(3, 11))
        n = int(rng.integers(120, 253))
        eshock = rng.normal(0.0, 1.5, n)
        mu = ar1(rng, (1, n), 0.99, 1.0)[0] if world == "13" else np.zeros(n)
        bid = rng.uniform(5.0, 60.0, (M, 1)) + np.zeros((M, n))
        L = rng.normal(0.0, 1.0, M)
        Le = float(L.mean())
        if world == "6":
            fav = np.zeros((M, 1))
            fav[0] = 1.0
            common = fav * eshock[None, :] + (1 - fav) * rng.normal(0.0, 0.2, (M, n))
        elif world == "8":
            common = eshock[None, :] * np.exp(0.5 * Le) + 0.0
        else:
            common = np.broadcast_to(eshock[None, :], (M, n))
        f = ar1(rng, (1, n), 0.8, 1.0)[0] if world == "7" else np.zeros(n)
        eta = f - 0.8 * np.concatenate([[0.0], f[:-1]])
        b = bid + common + rng.normal(0.0, 0.5, (M, n)) - (0.5 * eta[None, :] if world == "7" else 0.0) + (0.3 * 1.0 * mu[None, :] if world == "13" else 0.0)
        rho = (0.9 - 0.3 * ndtr(L))[:, None] if world == "8" else np.full((M, 1), 0.7)
        noise = np.stack([ar1(rng, (1, n), float(rho[j, 0]), 1.0)[0] for j in range(M)])
        if world == "6":
            s = np.where(np.arange(M)[:, None] == 0, 2.0 + 1.5 * np.abs(eshock)[None, :] + noise, 3.0 + noise)
        else:
            s = 2.0 + 1.5 * np.abs(eshock)[None, :] + noise
        s = np.maximum(1.0, np.round(s + f[None, :] * (1.0 if world == "7" else 0.0)))
        db = np.diff(b, axis=1, prepend=b[:, :1])
        da = np.diff(b + s, axis=1, prepend=(b + s)[:, :1])
        cl = db.sum(axis=0)[None, :] - db
        ca = da.sum(axis=0)[None, :] - da
        ds = np.diff(s, axis=1, prepend=s[:, :1])
        k = np.arange(2, n - 4)
        for j in range(M):
            y = s[j, k + 1] - s[j, k] + (mu[k + 1] * 0.5 if world == "13" else 0.0)
            tw = cl[j, k + 3] if False else (db.sum(axis=0)[k + 3] - db[j, k + 3])
            for key, val in (("market_id", np.full(len(k), f"{e}-{j}")), ("event_id", np.full(len(k), e)), ("slot", k), ("cl_sib", cl[j, k]), ("ca_sib", ca[j, k]), ("cl_tw", tw),
                             ("spread_k_c", s[j, k]), ("own_dspread_c", ds[j, k]), ("own_dbid_c", db[j, k]), ("n_elig", np.full(len(k), float(M))), ("y", y),
                             ("ctrl_liq", np.full(len(k), L[j]) + rng.normal(0.0, 0.5, len(k)))):
                rows[key].append(val)
    R = {k_: np.concatenate(v) for k_, v in rows.items()}
    df = _finish(R, "CH233")
    if world in ("5", "6", "7", "8"):
        df = df[rng.random(len(df)) >= 0.10].reset_index(drop=True)
    sc = float(np.nanstd(df["cl_sib"].to_numpy(float), ddof=1)) or 1.0
    df["zcl"] = df["cl_sib"] / sc
    df["zca"] = df["ca_sib"] / (float(np.nanstd(df["ca_sib"].to_numpy(float), ddof=1)) or 1.0)
    df["zcl_tw"] = df["cl_tw"] / sc
    df["arm"] = "primary"
    if world == "8":
        df["liq_proxy"] = df["ctrl_liq"]
    if effect:
        df["y"] = df["y"] + effect * df["zcl"]
    return df


# --- CH232 worlds (9-11, 14, 15) --------------------------------------------------------------------------------------------------------------


def world_ch232(world: str, rng: np.random.Generator, *, per_panel: int = 160, effect: float = 0.0) -> pd.DataFrame:
    """Worlds 9, 10, 11, 14 and 15: 160 rewarded and 160 control markets, ``n_m`` uniform on 120..252, a bounded logit walk (step SD 0.3) started uniformly in [0.06, 0.94];
    the unit population by 4.2's rules (approach zone, movers, first crossing of the UTC day, tick-coincident exclusion)."""
    mk = 2 * per_panel
    n_max = 252
    rew = np.r_[np.ones(per_panel), np.zeros(per_panel)]
    n_m = rng.integers(120, 253, mk)
    mu = ar1(rng, (mk, n_max), 0.99, 1.0) if world == "14" else np.zeros((mk, n_max))
    scale = np.exp(0.3 * mu * rew[:, None]) if world == "14" else 1.0
    lg = np.empty((mk, n_max))
    lg[:, 0] = logit(rng.uniform(0.06, 0.94, mk))
    st = rng.normal(0.0, 0.3, (mk, n_max)) * scale
    for t in range(1, n_max):
        lg[:, t] = np.clip(lg[:, t - 1] + st[:, t], logit(0.02), logit(0.98))
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
        if world == "14":
            spread = np.maximum(1.0, np.round(base + noise + mu * rew[:, None]))
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
    rows: dict[str, list] = {k: [] for k in ("market_id", "event_id", "slot", "rew", "d", "absd", "d_tow", "dist", "upper", "spread_k_c", "dspread_c", "xo", "xr", "y", "xo_tw", "dS_ticks", "S_ticks")}
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
        y = spread[m, kk + 1] - spread[m, kk] + effect * xo * (rew[m])
        tw_in = (mid[m, kk + 2] >= 0.10 - 1e-9) & (mid[m, kk + 2] <= 0.90 + 1e-9) & ((mid[m, kk + 3] < 0.10 - 1e-9) | (mid[m, kk + 3] > 0.90 + 1e-9))
        for key, val in (("market_id", np.full(len(idx), m)), ("event_id", np.full(len(idx), m // 3)), ("slot", kk), ("rew", np.full(len(idx), rew[m])), ("d", dk[idx]), ("absd", np.abs(dk[idx])),
                         ("d_tow", d_tow), ("dist", dist), ("upper", upper), ("spread_k_c", spread[m, kk]), ("dspread_c", spread[m, kk] - spread[m, kk - 1]), ("xo", xo), ("xr", xr),
                         ("y", y), ("xo_tw", tw_in.astype(float)), ("dS_ticks", np.round(spread[m, kk] - spread[m, kk - 1])), ("S_ticks", np.round(spread[m, kk]))):
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
EXTRA_CTRL = {"3": ("log1p_vol",), "3b": ("log1p_vol",), "8": ("liq_proxy",), "4": ()}


def generate(world: str, rng: np.random.Generator, *, effect: float = 0.0, small: bool = False) -> tuple[pd.DataFrame, str]:
    test, w = GENERATORS[world]
    kw = {"effect": effect}
    if small:
        kw.update({"CH234": {"markets": 60}, "CH233": {"events": 25}, "CH232": {"per_panel": 60}}[test])
    return {"CH234": world_ch234, "CH233": world_ch233, "CH232": world_ch232}[test](w, rng, **kw), test


def _controls(test: str, world: str, df: pd.DataFrame) -> list[str]:
    c = [x for x in CTRL[test] if x in df]
    if world == "8" and "liq_proxy" in df:
        c.append("liq_proxy")
    return c


def evaluate_world(world: str, sub_seed: int, spec: dict, *, stat: str, draws: int, effect: float = 0.0, small: bool = False) -> dict:
    """One world under its binding test: the gate rejection (the analysis' own gate path) or the verdict-size statistic (analytic p < 0.05 and F and the point
    condition hold; the gate is omitted)."""
    rng = np.random.default_rng(sub_seed)
    df, test = generate(world, rng, effect=effect, small=small)
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
               registered: bool = False, progress=None) -> dict:
    """``worlds`` worlds per scenario (one generator seeded ``seed``; the world sub-seeds are drawn in table order), each under its binding test and statistic
    (1.8). Criterion: rate <= ``0.05 + 1.645 sqrt(0.0475 / worlds)`` (0.058 at 2,000). Non-binding: the power runs (generators ``seed x 100 + n``). A failing gate
    scenario sets only its test to 'SE check failed (size scenario)', a failing verdict-size scenario to '(mechanical world)'; k unchanged; no rerun, reseed or
    redesign."""
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
            r = evaluate_world(sc, sub, spec, stat=sp["stat"], draws=draws, small=small)
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
        cf = spec.get("census_fixed") or {}
        if not isinstance(tests, list) or not tests or [t for t in tests if t not in TESTS] or set(tests) & set(spec.get("dropped_tests") or []):
            print("refusing: the registered size check needs k_tests filled with known, undropped tests (census values first)")
            return 2
        if any(v is None for t in tests for v in (cf.get(t) or {"x": None}).values() if False) or any(cf.get(t) is None for t in tests):
            print("refusing: census_fixed is not filled")
            return 2
    if int(spec["seeds"]["size_check"]) != REGISTERED_SEED:
        print("refusing: the spec's size-check seed is not 20261497")
        return 2
    out = size_check(worlds=worlds, draws=draws, seed=REGISTERED_SEED if not args.dev else DEV_SEED, spec=spec, tests=list(tests) if tests else None, registered=not args.dev,
                     power_worlds=int(sc["power_worlds"]) if not args.dev else int(getattr(args, "power_worlds", 0) or 0))
    out.update(code_sha256=lt.code_hashes(), spec_sha256=spec["_sha256"], design_text_sha256=lt.design_text_sha(), dev=bool(args.dev))
    return write_out(args.out, json.dumps(bd._clean(out), sort_keys=True, indent=1, default=str))
