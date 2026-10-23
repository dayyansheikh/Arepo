# ruff: noqa: E501
"""LT10 simulated worlds W1-W10 (LIVE_TESTS_10.md 1.8.1): synthetic pair x 120 s poll grids, evaluated through the READER'S OWN builders
(``live_tests10.build_origins``, ``targets``, ``twins``, ``population``, ``add_test_columns``) so that every declared control is computed from the simulated
polls exactly as the reader computes it. Research tooling only; no data is read; no network.

Common (1.8.1): 30 events and 60 pairs (12 events of one pair, 9 of two, 6 of three, 3 of four); 7 UTC days; polls every 120 s (720 a pair-day), origins
every 600 s; prices in cents on a 1c tick (10% of pairs on a 0.1c Polymarket tick); 15% of each pair's grid origins dropped from the unit set at random and
independently. W1: a latent efficient price per pair (random walk, per-poll innovation SD 0.15c) plus event jumps (per poll per event probability 0.002, size
N(0, (2c)^2), hitting every pair of the event); each venue's mid = latent + AR(0.5) noise of SD 0.3c, rounded to the tick, updated simultaneously on both
venues; spreads reflected AR(1) on ticks (rho 0.9, mean 2 ticks, floor 1 tick); touch sizes log-normal AR(0.9) (SD 0.5); Kalshi trades Bernoulli(0.05) a poll,
a trade setting ``k_last`` to the touch on a random side and adding |N(0, 1)| x 100 to ``k_vol24``, which decays by 1/720 of its value a poll.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy.signal import lfilter

from . import live_tests10 as lt

POLL_S = lt.POLL_S
DAY_POLLS = 720
T_BASE = int(lt.epoch("2026-11-10T00:00:00Z"))  # a multiple of 86400 and of 600
WORLDS = ("W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8", "W9", "W10")
STD_PLAN = [1] * 12 + [2] * 9 + [3] * 6 + [4] * 3  # 30 events, 60 pairs
BIG_PLAN = [20] + [1] * 64  # 65 events, 84 pairs; G_eff = 84^2 / (400 + 64) = 15.2
DROP = 0.15
FLAGS = {
    "W1": {},
    "W2": {"vol": True},
    "W3": {"lag": 2},
    "W4": {"lag": 2, "klast_reset": True},
    "W5": {"lag": 2, "activity": True},
    "W6": {"bot": True},
    "W7": {"vol": True, "withdraw": True},
    "W8": {"alt_spreads": True},
    "W9": {"drift": True},
    "W10": {"vol": True, "jump_spreads": True, "big": True, "contiguous": True},
}
L_POLLS = math.ceil(lt.L_S / POLL_S)  # 95: no unit for the first L = 11,400 s after entry (not_yet_in_force)
RETIRE_POLLS = int(lt.b.RETIRE_KEEP_S // POLL_S)  # 190: polls continue for RETIRE_KEEP_S = 22,800 s after retirement


def ar1(rng, shape, rho: float, sd: float = 1.0) -> np.ndarray:
    """Stationary AR(1) along the last axis with stationary SD ``sd``."""
    e = rng.normal(0.0, sd * math.sqrt(1.0 - rho**2), shape)
    e[..., 0] = rng.normal(0.0, sd, shape[:-1])
    return lfilter([1.0], [1.0, -rho], e, axis=-1)


def reflect(u: np.ndarray, lo: float, hi: float) -> np.ndarray:
    """Reflect a path into [lo, hi] (triangle wave)."""
    w = (u - lo) / (hi - lo)
    return lo + (hi - lo) * np.abs(((w + 1.0) % 2.0) - 1.0)


def _ffill_price(event: np.ndarray, price: np.ndarray, init: np.ndarray) -> np.ndarray:
    """Per row, the price at the last event poll (``init`` before the first)."""
    n = event.shape[1]
    idx = np.where(event, np.arange(n)[None, :], -1)
    idx = np.maximum.accumulate(idx, axis=1)
    out = np.take_along_axis(price, np.maximum(idx, 0), axis=1)
    return np.where(idx >= 0, out, init[:, None])


def _round_tick(x: np.ndarray, tick) -> np.ndarray:
    return np.round(x / tick) * tick


def simulate(world: str, rng: np.random.Generator, *, plan: list[int] | None = None, days: int | None = None) -> dict:
    """One world: the grid arrays ``A`` (``live_tests10.GRID_FIELDS`` + ``present`` + ``k_active``, pair x poll), the pair / event structure, the per-origin
    pair status and the origin columns. Nothing is estimated here."""
    f = FLAGS[world]
    plan = plan if plan is not None else (BIG_PLAN if f.get("big") else STD_PLAN)
    days = days if days is not None else (21 if f.get("big") else 7)
    E = len(plan)
    ev_of = np.repeat(np.arange(E), plan)
    P = len(ev_of)
    n = days * DAY_POLLS
    j = np.arange(n)
    hour = ((T_BASE + POLL_S * j) // 3600) % 24
    # volatility, activity, drift, jumps ---------------------------------------------------------------------------------------------------
    v = ar1(rng, (E, n), 0.9 ** (1 / 5), 0.5) if f.get("vol") else np.zeros((E, n))
    diurnal = 0.5 * np.sin(2 * math.pi * (hour - 14) / 24.0) if f.get("vol") else np.zeros(n)
    mult_e = np.exp(v + diurnal[None, :])
    mult = mult_e[ev_of]
    jump_flag = rng.random((E, n)) < 0.002
    jump_amt = jump_flag * rng.normal(0.0, 0.02, (E, n))
    eps = rng.normal(0.0, 0.0015, (P, n)) * mult
    x = reflect(0.5 + np.cumsum(eps + jump_amt[ev_of], axis=1), 0.1, 0.9)
    nk, npol = ar1(rng, (P, n), 0.5, 0.003), ar1(rng, (P, n), 0.5, 0.003)
    # Polymarket's mid: simultaneous (W1) or lagged behind Kalshi's level (W3-W5)
    if f.get("activity"):
        a = ar1(rng, (P, n), 0.95 ** (1 / 5), 1.0)
        lag = np.where(a > 0, 1, 3)
    else:
        a = np.zeros((P, n))
        lag = np.full((P, n), f.get("lag", 0))
    xl = np.take_along_axis(x, np.maximum(j[None, :] - lag, 0), axis=1)
    # DESIGN-AMBIGUITY: W3 says 'Kalshi's mid = x_t and Polymarket's mid = x_{t-2}'; W1's venue AR(0.5) noise is kept on both (W3 = W1 with the lag).
    km = x + nk
    pm = (xl if (f.get("lag") or f.get("activity")) else x) + npol
    pt = np.where(rng.random(P) < 0.10, 0.001, 0.01)[:, None]
    km_r, pm_r = _round_tick(km, 0.01), _round_tick(pm, pt)
    # spreads in ticks ----------------------------------------------------------------------------------------------------------------------
    drift = ar1(rng, (1, n), 0.999, 0.5) if f.get("drift") else 0.0
    if f.get("alt_spreads"):
        sp_ticks = reflect(2.0 + ar1(rng, (P, n), 0.7 ** (1 / 5), 1.0) + drift, 1.0, 40.0)
        steps = np.where(rng.random((P, n)) < 0.1, rng.choice([-1, 1], (P, n)), 0)
        sk = np.empty((P, n))
        cur = np.full(P, 2.0)
        for jj in range(n):
            cur = np.clip(cur + steps[:, jj], 1, 10)
            sk[:, jj] = cur
        sk_ticks = sk + drift
    else:
        sk_ticks = reflect(2.0 + ar1(rng, (P, n), 0.9, 1.0) + drift, 1.0, 40.0)
        sp_ticks = reflect(2.0 + ar1(rng, (P, n), 0.9, 1.0) + drift, 1.0, 40.0)
    if f.get("jump_spreads"):
        q = lfilter([1.0], [1.0, -0.9], jump_flag.astype(float), axis=1)[ev_of]
        sk_ticks, sp_ticks = sk_ticks + q, sp_ticks + q
    sk_ticks = np.maximum(np.round(sk_ticks), 1.0)
    sp_price = np.maximum(np.round(sp_ticks), 1.0) * pt
    if f.get("lag") or f.get("activity"):  # the displayed spread widens by |dx| / 2 for one poll after each move
        dpm = np.abs(np.diff(pm_r, axis=1, prepend=pm_r[:, :1]))
        sp_price = sp_price + np.concatenate([np.zeros((P, 1)), dpm[:, :-1]], axis=1) / 2.0
    # sizes -------------------------------------------------------------------------------------------------------------------------------------
    sz = np.stack([np.exp(math.log(100.0) + ar1(rng, (P, n), 0.9, 0.5) * (mult if f.get("vol") else 1.0)) for _ in range(4)])
    kbs, kas, pbs, pas_ = sz[0], sz[1], sz[2], sz[3]
    # DESIGN-AMBIGUITY: W6's period of 5 polls equals the 10-minute origin spacing, so t and s0 share the bot's phase and the reset rarely makes a pull; implemented literally.
    if f.get("bot"):  # Kalshi sizes reset by a bot every 5 polls on a fixed phase per pair: 30% at the reset, refilled over two polls
        phase = rng.integers(0, 5, P)[:, None]
        k = (j[None, :] - phase) % 5
        fac = np.where(k == 0, 0.3, np.where(k == 1, 0.65, 1.0))
        kbs, kas = kbs * fac, kas * fac
    kb_price = np.maximum(_round_tick(km_r - sk_ticks * 0.01 / 2.0, 0.01), 0.01)
    ka_price = kb_price + sk_ticks * 0.01
    pb_price = np.maximum(_round_tick(pm_r - sp_price / 2.0, pt), pt)
    pa_price = pb_price + sp_price
    # W7: a withdrawal inside a quiet window: probability logistic(-3.4 + 0.8 z(v_e)) per origin window -----------------------------------------------
    if f.get("withdraw"):
        z = (v / 0.5)[ev_of]
        pw = 1.0 / (1.0 + np.exp(-(-3.4 + 0.8 * z)))
        at = (j % 5 == 0)[None, :] & (rng.random((P, n)) < pw)
        two_ticks = at & (rng.random((P, n)) < 0.5)
        kb_price = np.where(two_ticks, kb_price - 0.01, kb_price)
        ka_price = np.where(two_ticks, ka_price + 0.01, ka_price)
        fall = at & ~two_ticks
        bid_side = rng.random((P, n)) < 0.5
        kbs = np.where(fall & bid_side, kbs * 0.4, kbs)
        kas = np.where(fall & ~bid_side, kas * 0.4, kas)
    # trades, k_last, k_vol24 -----------------------------------------------------------------------------------------------------------------------
    logit = math.log(0.05 / 0.95) + (0.5 * (v / 0.5)[ev_of] if f.get("vol") else 0.0) + (1.0 * a if f.get("activity") else 0.0)
    ptrade = 1.0 / (1.0 + np.exp(-logit))
    if f.get("jump_spreads"):
        ptrade = np.where(jump_flag[ev_of], 0.5, ptrade)
    trade = rng.random((P, n)) < ptrade
    side_ask = rng.random((P, n)) < 0.5
    tprice = np.where(side_ask, ka_price, kb_price)
    event = trade.copy()
    price = np.where(trade, tprice, np.nan)
    if f.get("klast_reset"):
        sel = rng.random(24) < 0.3
        reset = ((j % 15) == 0) | (((T_BASE + POLL_S * j) % 3600 == 0) & sel[hour])
        reset = np.broadcast_to(reset[None, :], (P, n))
        price = np.where(reset & ~trade, km_r, price)
        event = event | reset
    klast = _ffill_price(event, np.where(np.isfinite(price), price, 0.0), km_r[:, 0])
    inc = trade * np.abs(rng.normal(0.0, 1.0, (P, n))) * 100.0
    decay = 1.0 - 1.0 / 720.0
    kvol = lfilter([1.0], [1.0, -decay], inc, axis=1) + 2800.0 * decay ** j[None, :]
    # presence, status and the origin grid ---------------------------------------------------------------------------------------------------------
    present = np.ones((P, n), bool)
    entry = np.full(P, -10**9, dtype=np.int64)  # listed from the start: no entry loss
    retire = np.full(P, n, int)
    if f.get("contiguous"):
        big, rest = np.flatnonzero(ev_of == 0), np.flatnonzero(ev_of > 0)  # one pair in four within each event kind: 5 of the 20-pair event, 16 of the 64 singletons
        chosen = np.concatenate([np.sort(rng.choice(big, max(1, round(len(big) / 4)), replace=False)), np.sort(rng.choice(rest, max(1, round(len(rest) / 4)), replace=False))])
        for p in chosen:
            entry[p] = int(rng.integers(0, n - 1))
            retire[p] = int(rng.integers(entry[p], n))
        present = (j[None, :] >= entry[:, None]) & (j[None, :] <= (retire + RETIRE_POLLS)[:, None])
    cols = np.arange(35, n - 22, 5)  # first origin with a full look-back (t - 3,840 s); last with a full +2,520 s twin window
    K = len(cols)
    st = np.full((P, K), lt.ST["unit"], dtype=np.int64)
    st = np.where(cols[None, :] < (entry + L_POLLS)[:, None], lt.ST["not_yet_in_force"], st)
    st = np.where(cols[None, :] > retire[:, None], lt.ST["retired"], st)
    A = {k_: np.full((P, n), np.nan) for k_ in lt.GRID_FIELDS}
    A.update(k_bid=kb_price, k_ask=ka_price, k_last=klast, k_bid_sz=kbs, k_ask_sz=kas, k_vol24=kvol, p_bid=pb_price, p_ask=pa_price, p_bid_sz=pbs, p_ask_sz=pas_,
             p_tick=np.broadcast_to(pt, (P, n)).copy(), k_recv=T_BASE + POLL_S * j[None, :] + 1.0 + 2.0 * rng.random((P, n)),
             p_recv=T_BASE + POLL_S * j[None, :] + 2.0 + 2.0 * rng.random((P, n)))
    for k_ in ("k_bid", "k_ask", "k_last", "k_bid_sz", "k_ask_sz", "k_vol24", "p_bid", "p_ask", "p_bid_sz", "p_ask_sz", "p_tick", "k_recv", "p_recv"):
        A[k_] = np.where(present, A[k_], np.nan)
    A["present"], A["k_active"] = present, present.copy()
    return {"A": A, "ev_of": ev_of, "P": P, "n": n, "cols": cols, "pair_st": st, "plan": plan, "days": days, "world": world, "x": x, "pt": pt[:, 0], "entry": entry,
            "retire": retire, "jump_flag": jump_flag, "v": v}


def origin_frame(S: dict, rng: np.random.Generator) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The reader's own origin pass over the world (statuses and states), the 15% independent origin drop, the targets (+20 min) and the Kalshi-only twins of
    the units. Returns ``(units, twins)`` aligned row for row."""
    A, P, cols = S["A"], S["P"], S["cols"]
    K = len(cols)
    meta = {"pid": np.array([f"w{i}" for i in range(P)], dtype=object), "pair_st": S["pair_st"], "cat_known": np.ones((P, K), bool), "sports": np.zeros((P, K), bool),
            "crypto": np.full((P, K), "non_crypto", dtype=object), "ev": np.repeat(np.array([f"e{e}" for e in S["ev_of"]], dtype=object)[:, None], K, axis=1),
            "p_end": np.full((P, K), T_BASE + 1e9), "k_close": np.full((P, K), T_BASE + 1e9), "hv": np.zeros((P, K), bool), "fee": np.full((P, K), np.nan), "exclude_event": None}
    df = lt.build_origins(A, T_BASE, cols, meta, check_e009=False)
    tg = lt.targets(A, T_BASE, cols, 10)
    keep = (df["status"].to_numpy() == lt.ST["unit"]) & (rng.random(P * K) >= DROP)
    rows_i = np.repeat(np.arange(P), K)
    cols_i = np.tile(cols, P)
    u = pd.concat([df.reset_index(drop=True), tg.reset_index(drop=True)], axis=1)[keep].reset_index(drop=True)
    tw = lt.twins(A, T_BASE, cols_i[keep][None, :].astype(np.int64), rows_i[keep][None, :]).reset_index(drop=True)
    return u, tw


def test_frame(u: pd.DataFrame, tw: pd.DataFrame, test: str, spec: dict | None) -> tuple[pd.DataFrame, np.ndarray]:
    """The test's population with the census scale / centres (the spec's census-fixed values, else this world's own pooled values: dev only) and its
    target in cents (sections 2-4). Pair / event / day aliases for the estimators."""
    U = pd.concat([u, tw], axis=1)
    cf = (spec or {}).get("census_fixed") or {}
    scale = cf.get("scale_K_cents") / 100.0 if cf.get("scale_K_cents") else float(np.nanstd(U["dsK"].to_numpy(float), ddof=1))
    rv = cf.get("rv60") if cf.get("rv60") and all(cf["rv60"][z].get(w) is not None for z in ("rv60_P", "rv60_K") for w in ("centre", "scale")) else \
        {k: {"centre": float(np.nanmean(U[k])), "scale": float(np.nanstd(U[k], ddof=1))} for k in ("rv60_P", "rv60_K")}
    X = lt.add_test_columns(U, scale if scale > 0 else None, rv)
    X = lt.population(X, test).reset_index(drop=True)
    X["market_id"], X["t_row"], X["event_id"] = X["pid"].astype(str), X["t"].astype(float), X["ev"].astype(str)
    X["block2"] = ((X["t"].to_numpy(float) - T_BASE) // (2 * lt.DAY_S)).astype(int)
    good = X["tg_status"].to_numpy() == 0
    pm, h = X["pmid"].to_numpy(float), X["pmid_h"].to_numpy(float)
    if test == "CH224":
        y = (X["sP_h"].to_numpy(float) - X["sP_t"].to_numpy(float)) * 100.0
    elif test == "CH223":
        y = np.abs(h - pm) * 100.0
    else:
        y = X["sign"].to_numpy(float) * (h - pm) * 100.0
    return X, np.where(good, y, np.nan)
