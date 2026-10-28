# ruff: noqa: E501
"""LT12 simulated worlds 1-10, world R1, world 1's loading bisection and the size check (LIVE_TESTS_12.md 1.8, 1.8.1). Research tooling only; no data is
read; no network.

LT12 ambiguity A20 (= LT11 A10): the worlds generate the ANALYSIS FRAME directly (the columns the primary model reads, with the declared controls computed
from the simulated paths), not raw captures pushed through the reader's builders. The gate path (``live_tests12.event_day_state_shift_gate`` through
``analysis.gate``: raw shift, demeaning re-applied every draw, the gate-sample refit and its event-clustered CR1 t, the 16-capture minimum and the omission
rule), the estimator (``analysis.fit12``), the F rule and the point conditions are the analysis' own. The generators are conventions (1.8.1), fixed before
any world was evaluated and never tuned.

Common (1.8.1): units on a 2 h grid of 252 slots (``day = slot // 12``, ``block2 = day // 2``); each event placed at a uniform start on the common grid
(the venue-wide factor of world 3 is one series over the grid); spreads in cents on a 1c grid with a 1c floor; 10% of member units removed at random after
generation; every event has a series family (40 families, uniform, worlds 1-6) and its own event-id set, so the placebo rule of 2.3 applies.
"""

from __future__ import annotations

import hashlib
import json
import math

import numpy as np
import pandas as pd
from scipy.signal import lfilter
from scipy.special import ndtr

from . import bounce_decomp as bd
from . import live_tests12 as lt
from . import live_tests12_analysis as an

TESTS = lt.TESTS
REGISTERED_SEED = 20261597
DEV_SEED = REGISTERED_SEED * 100 + 99  # development runs never use the registered seed (1.8: no preliminary run at 20261597)
TIMING_SEED = REGISTERED_SEED * 100 + 98  # 8.4 step 3: "a timing seed other than 20261597" (and not the development seed)
CALIB_SEED = REGISTERED_SEED * 100 + 61  # 1.8.1 world 1's calibration (the registered post-census calibration ONLY)
R1_SEED = REGISTERED_SEED * 100 + 54  # 1.8 world R1 (the registered run only)
POWER_SEEDS = {"CH245": REGISTERED_SEED * 100 + 51, "CH244": REGISTERED_SEED * 100 + 52}  # the registered run only
# Every derived generator is the run's own master seed x 100 + n (n = 51, 52 power; 54 R1; 61 calibration), so a development, test or timing run (master
# seed != 20261597) never touches a registered seed; a run whose master seed IS one of these is refused unless it is the registered run itself.
REGISTERED_SEEDS = frozenset({REGISTERED_SEED, CALIB_SEED, R1_SEED, *POWER_SEEDS.values()})


def derived_seed(master: int, n: int) -> int:
    """The derived generator ``master x 100 + n`` of a run (1.8: power runs x 100 + 51 / 52, world R1 x 100 + 54, world 1's calibration x 100 + 61)."""
    return int(master) * 100 + int(n)


def seed_guard(seed: int, *, registered: bool) -> None:
    """No preliminary run at the registered seed or at any registered derived seed (1.8): only the registered run may use 20261597 (and through it the
    derived seeds); every other run is refused at any of them, and the registered run itself must use 20261597."""
    if registered and seed != REGISTERED_SEED:
        return  # a test of the registered code path at a non-registered master seed: its derived seeds are non-registered too
    if seed in REGISTERED_SEEDS and not (registered and seed == REGISTERED_SEED):
        raise Refused(f"seed {seed} is a registered seed (20261597 or a registered derived seed): only the registered size check may use it (1.8: no preliminary run)")
SLOTS = 252
SLOT_S = 7200.0
SCENARIO_ORDER = ("1", "2", "3", "4", "5", "6", "7", "8", "9", "10")
SCENARIOS: dict[str, dict] = {**{s: {"test": "CH245", "stat": "gate"} for s in ("1", "2", "3", "4", "5")}, "6": {"test": "CH245", "stat": "verdict"},
                              **{s: {"test": "CH244", "stat": "gate"} for s in ("7", "8", "9")}, "10": {"test": "CH244", "stat": "verdict"}}
FROZEN_LIMIT = 0.058  # 1.8: limit 0.058 at 2,000 worlds (frozen value)
FROZEN_WORLDS = 2000
MQ_RHO, MQ_SD, MQ_LOADING = 0.99, 0.5, 0.3  # worlds 6 and 10
R1_LOADING = 0.4
FAMILIES = 40
DEV_CAL = {"rho_census": 0.64, "rgap_q50_s": 5.0, "rgap_q90_s": 30.0, "world9_corr": -0.20}  # development / timing placeholders only (labelled; never a size result)


class Refused(RuntimeError):
    """The size check refuses (a registered seed on a development run, an unknown scenario, an unfilled census value)."""


def limit_for(worlds: int) -> float:
    return FROZEN_LIMIT if worlds == FROZEN_WORLDS else 0.05 + 1.645 * math.sqrt(0.0475 / worlds)


def ar1(rng, shape, rho: float, sd: float = 1.0) -> np.ndarray:
    """AR(1) series along the last axis with STATIONARY standard deviation ``sd`` (started in the stationary law)."""
    e = rng.normal(0.0, sd * math.sqrt(1.0 - rho**2), shape)
    e[..., 0] = rng.normal(0.0, sd, shape[:-1])
    return lfilter([1.0], [1.0, -rho], e, axis=-1)


def floor_round(x) -> np.ndarray:
    """Cents on the 1c grid with the 1c floor (1.8.1)."""
    return np.maximum(1.0, np.round(np.asarray(x, float)))


def _place(rng, n: int) -> int:
    return int(rng.integers(0, SLOTS - n + 1))


def _remove(df: pd.DataFrame, rng) -> pd.DataFrame:
    """1.8.1: 10% of member units removed at random after generation (exercises the omission rule)."""
    return df[rng.random(len(df)) >= 0.10].reset_index(drop=True)


def _finish(df: pd.DataFrame) -> pd.DataFrame:
    df["t_row"] = df["slot"].to_numpy(float) * SLOT_S
    df["day"] = (df["slot"].to_numpy(int) // 12).astype(str)
    df["block2"] = (df["slot"].to_numpy(int) // 24).astype(int)
    df["arm"], df["f_end_ok"] = "primary", 1.0
    for s_ in range(1, 12):
        df[f"sd{s_}"] = ((df["slot"].to_numpy(int) % 12) == s_).astype(float)
    return df


# --- world 1's loading (1.8.1, re-check fix 2, final verification fix 3) ------------------------------------------------------------------


def calib_corr(lam: float, *, slots: int, seed: int) -> float:
    """The planted within-event same-slot correlation of the two books' spread innovations (after rounding and the 1c floor) on ONE two-member event of
    ``slots`` slots generated as world 1 (``v`` AR(1) 0.8 SD 1, ``u`` AR(0.5) SD 0.8c per book) at the calibration seed (the same draws at every step)."""
    rng = np.random.default_rng(seed)
    v = ar1(rng, (slots,), 0.8, 1.0)
    u = ar1(rng, (2, slots), 0.5, 0.8)
    s = floor_round(2.0 + lam * v[None, :] + u)
    d = np.diff(s, axis=1)
    if d[0].std() == 0 or d[1].std() == 0:
        return float("nan")
    return float(np.corrcoef(d[0], d[1])[0, 1])


def world1_lambda(rho_census, spec: dict, *, seed: int) -> dict:
    """1.8.1: ``lambda`` such that the planted correlation equals ``rho_ss = max(rho_census, 0.64)``: bisection on [0, 10] to within 0.005, at most 40 steps,
    each step a calibration run (:func:`calib_corr`). Failure rule: ``rho_census`` NaN, ``rho_ss`` not bracketed by the calibration correlations at 0 and 10,
    or no convergence within 40 steps -> world 1 (and world 3, which inherits ``lambda``) is not run: 'SE check failed (size scenario)' for CH245; no other
    bracket, step count, seed or loading is tried."""
    # re-check fix 2 (world 1's loading) and final verification fix 3 (failure rule): bracket, tolerance, step limit, slots and seed from the spec block
    w = spec["size_check"]["world1"]
    lo, hi = (float(x) for x in w["bracket"])
    tol, steps, slots = float(w["tol"]), int(w["max_steps"]), int(w["slots"])
    if seed == CALIB_SEED and int(w["seed"]) != CALIB_SEED:
        raise Refused("the spec's world-1 calibration seed is not 20261597 x 100 + 61")
    if rho_census is None or not isinstance(rho_census, (int, float)) or not math.isfinite(float(rho_census)):
        return {"ok": False, "reason": "rho_census is NaN", "lambda": None}
    rho_ss = max(float(rho_census), float(w["rho_floor"]))
    c_lo, c_hi = calib_corr(lo, slots=slots, seed=seed), calib_corr(hi, slots=slots, seed=seed)
    out = {"rho_census": float(rho_census), "rho_ss": rho_ss, "corr_at_lo": c_lo, "corr_at_hi": c_hi, "bracket": [lo, hi], "tol": tol, "max_steps": steps}
    if not (math.isfinite(c_lo) and math.isfinite(c_hi) and min(c_lo, c_hi) <= rho_ss <= max(c_lo, c_hi)):
        return {**out, "ok": False, "reason": "rho_ss not bracketed by the calibration correlations at lambda = 0 and 10", "lambda": None}
    for i in range(1, steps + 1):
        mid = (lo + hi) / 2.0
        c = calib_corr(mid, slots=slots, seed=seed)
        if math.isfinite(c) and abs(c - rho_ss) <= tol:
            return {**out, "ok": True, "lambda": mid, "corr": c, "steps": i}
        if (c - rho_ss) * (c_lo - rho_ss) > 0:
            lo, c_lo = mid, c
        else:
            hi = mid
    return {**out, "ok": False, "reason": f"tolerance {tol} not reached within {steps} bisection steps", "lambda": None}


def gap_sampler(q50: float, q90: float, floor_q50: float):
    """World 2's receipt gaps (1.8.1): a lognormal through the census q50 (floor 5 s) and q90 (LT12 ambiguity A21: the distribution family)."""
    m = max(float(q50), float(floor_q50))
    q9 = max(float(q90), m)
    sig = math.log(q9 / m) / 1.2815515655446004 if q9 > m else 0.0

    def draw(rng, size):
        return m * np.exp(sig * rng.standard_normal(size))

    return draw


# --- CH245 worlds (1-6, R1) ------------------------------------------------------------------------------------------------------------------


def _ch245_lines(e: int, start: int, sA: np.ndarray, sB: np.ndarray, extra: dict, rng) -> list[dict]:
    """Thin and dense lines (2.2-2.3) of one simulated pair: units at captures k = 1 .. n - 4 (k - 1 .. k + 3 exist); the thin member is the wider book at
    k - 1 (``|sA - sB| >= 1c``, the 1c tick); a pair-capture with equal spreads at k - 1 is ``sym`` (no unit)."""
    n = len(sA)
    S = np.stack([sA, sB])
    rows = []
    for k in range(1, n - 3):
        if abs(S[0, k - 1] - S[1, k - 1]) < 1.0 - 1e-9:
            continue
        th = 0 if S[0, k - 1] > S[1, k - 1] else 1
        for i, o, line in ((th, 1 - th, "thin"), (1 - th, th, "dense")):
            r = {"event_id": f"e{e}", "nrkey": f"e{e}", "market_id": f"e{e}-{i}", "o_market_id": f"e{e}-{o}", "slot": start + k, "line": line, "k_local": k,
                 "y": S[i, k + 1] - S[i, k], "o_ds_c": S[o, k] - S[o, k - 1], "own_ds_c": S[i, k] - S[i, k - 1], "o_spread_km1_c": S[o, k - 1], "spread_c": S[i, k],
                 "o_ds_tw_c": S[o, k + 3] - S[o, k + 2], "o_spread_k_ticks": S[o, k], "own_spread_k_ticks": S[i, k], "own_first": float(rng.random() < 0.5)}
            for nm, arr in extra.items():
                r[nm] = arr[k] if np.ndim(arr) else arr
            rows.append(r)
    return rows


def _placebo(df: pd.DataFrame, fam: dict[str, int]) -> np.ndarray:
    """2.3's rule on the simulated thin units: per slot, events ordered by ``sha256(event key)``; the first later event (wrapping) of a different series
    family (event-id sets are disjoint by construction); its raw dense innovation."""
    out = np.full(len(df), np.nan)
    T = df[df["line"] == "thin"]
    for _s, g in T.groupby("slot"):
        keys = sorted(g["event_id"].tolist(), key=lambda k_: hashlib.sha256(k_.encode()).hexdigest())
        if len(keys) < 2:
            continue
        val = dict(zip(g["event_id"], g["o_ds_c"], strict=True))
        pos = {k_: i for i, k_ in enumerate(keys)}
        for idx, e in zip(g.index, g["event_id"], strict=True):
            for step in range(1, len(keys)):
                e2 = keys[(pos[e] + step) % len(keys)]
                if fam[e2] != fam[e]:
                    out[idx] = val[e2]
                    break
    return out


def world_ch245(world: str, rng: np.random.Generator, *, events: int = 300, effect: float = 0.0, cal: dict | None = None, cross: float = 0.0) -> pd.DataFrame:
    """Worlds 1-6 and R1 (``cross`` > 0, world 4's pairs with each book's next spread change loading ``cross`` per SD on the other book's innovation in both
    directions). ``cal`` holds world 1's ``lambda`` and world 2's receipt-gap quantiles. ``effect`` = cents per tercile gap of ``zs_D`` (power run)."""
    cal = cal or {}
    lam = cal.get("lambda")
    Fv = ar1(rng, (SLOTS,), 0.8, 0.6) if world == "3" else np.zeros(SLOTS)
    gap = gap_sampler(cal.get("rgap_q50_s", DEV_CAL["rgap_q50_s"]), cal.get("rgap_q90_s", DEV_CAL["rgap_q90_s"]), 5.0) if world == "2" else None
    rows: list[dict] = []
    fam: dict[str, int] = {}
    for e in range(events):
        n = int(rng.integers(8, SLOTS + 1))  # re-check fix 2: n uniform on 8..252 (worlds 1-6 and R1), so events with n_e < 16 occur
        st = _place(rng, n)
        fam[f"e{e}"] = int(rng.integers(0, FAMILIES))
        # code-freeze check fix 1: world 6's slow drift is drawn per EVENT (1.8 table "a slow event drift"; LT11 world 13's form), so the placebo partner
        # (another event in the slot) carries its own drift, not the identical market-wide one; drawn only in world 6 (no other world's draws move)
        mu = ar1(rng, (n,), MQ_RHO, MQ_SD) if world == "6" else None
        extra: dict = {}
        if world in ("1", "2", "3"):
            v = ar1(rng, (n,), 0.8, 1.0) if world in ("1", "3") else np.zeros(n)
            u = ar1(rng, (2, n), 0.5, 0.8)
            base = 2.0 + (float(lam) * v[None, :] if world in ("1", "3") else 0.0) + u + Fv[st:st + n][None, :]
            if world == "2":
                lvl = np.zeros((2, n))
                times = np.sort(rng.uniform(0.0, n * SLOT_S, rng.poisson(0.4 * n)))
                lag = rng.exponential(60.0, len(times))
                c, sgn = 0, []
                for _ in times:  # the shared step: +-1c, reflected in [0, 6]c (LT12 ambiguity A21)
                    s_ = 1 if rng.random() < 0.5 else -1
                    if not (0 <= c + s_ <= 6):
                        s_ = -s_
                    c += s_
                    sgn.append(s_)
                sgn = np.asarray(sgn, float)
                rB = np.arange(n) * SLOT_S + rng.uniform(0.0, 600.0, n)
                rA = rB + np.where(rng.random(n) < 0.5, 1.0, -1.0) * gap(rng, n)
                cs = np.concatenate([[0.0], np.cumsum(sgn)])
                lvl[1] = cs[np.searchsorted(times, rB, side="right")]  # book B updates at the step time
                tA = np.sort(times + lag)
                csA = np.concatenate([[0.0], np.cumsum(sgn[np.argsort(times + lag)])])
                lvl[0] = csA[np.searchsorted(tA, rA, side="right")]  # book A after the lag L ~ Exp(60 s); a straddling step shows in B at k and A at k + 1
                base = base + lvl
            S = floor_round(base)
            extra["rv_proxy"] = (v if world in ("1", "3") else 0.0) + rng.normal(0.0, 0.7, n)
        else:
            means = 2.0 + 2.0 * rng.exponential(1.0, 2)
            thin_b = int(np.argmax(means))
            Le = float(rng.normal())
            rho = np.full(2, 0.7)
            sd_e = np.full(2, math.sqrt(1.0 - 0.7**2))
            if world == "5":
                rho[thin_b] = 0.9 - 0.3 * float(ndtr(Le))
                sd_e[thin_b] = math.sqrt(1.0 - rho[thin_b] ** 2)
                sd_e[1 - thin_b] *= math.exp(0.5 * Le)
            if cross > 0:
                x = np.zeros((2, n))
                x[:, 0] = rng.normal(0.0, 1.0, 2)
                S = np.zeros((2, n))
                S[:, 0] = floor_round(means + x[:, 0])
                sd_d = math.sqrt(2.0 * (1.0 - 0.7))
                for t in range(1, n):
                    dprev = (S[:, t - 1] - S[:, t - 2]) if t >= 2 else np.zeros(2)
                    x[:, t] = rho * x[:, t - 1] + rng.normal(0.0, 1.0, 2) * sd_e + cross * (dprev[::-1] / sd_d)
                    S[:, t] = floor_round(means + x[:, t])
            else:
                x = np.stack([lfilter([1.0], [1.0, -rho[b_]], np.r_[rng.normal(0.0, sd_e[b_] / math.sqrt(1.0 - rho[b_] ** 2)), rng.normal(0.0, sd_e[b_], n - 1)]) for b_ in range(2)])
                S = floor_round(means[:, None] + x)
            if world == "5":
                extra["liq_proxy"] = Le + rng.normal(0.0, 0.5, n)
            if world == "6":
                extra["mu_k"], extra["mu_k1"], extra["mu_k3"] = mu, np.r_[mu[1:], 0.0], np.r_[mu[3:], np.zeros(3)]
        rows.extend(_ch245_lines(e, st, S[0], S[1], extra, rng))
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    if world == "6":  # the drift enters the thin book's target (at k + 1) and, at 0.3 per SD, the dense book's innovation at k and its twin at k + 3 (LT11 A27's form)
        th = df["line"].to_numpy() == "thin"
        df.loc[th, "y"] = df.loc[th, "y"].to_numpy(float) + df.loc[th, "mu_k1"].to_numpy(float)
        sd_o = float(np.nanstd(df.loc[th, "o_ds_c"].to_numpy(float)))
        df.loc[th, "o_ds_c"] = df.loc[th, "o_ds_c"].to_numpy(float) + MQ_LOADING * sd_o * df.loc[th, "mu_k"].to_numpy(float) / MQ_SD
        df.loc[th, "o_ds_tw_c"] = df.loc[th, "o_ds_tw_c"].to_numpy(float) + MQ_LOADING * sd_o * df.loc[th, "mu_k3"].to_numpy(float) / MQ_SD
    df = _finish(df)
    df["fam"] = df["event_id"].map(fam).astype(str)
    df["pl_ds_c"] = _placebo(df, fam)
    df = _remove(df, rng)
    th = df["line"] == "thin"
    sD = float(np.std(df.loc[th, "o_ds_c"].to_numpy(float))) or 1.0
    sT = float(np.std(df.loc[th, "own_ds_c"].to_numpy(float))) or 1.0
    sc = np.where(th, sD, sT)
    df["zs"], df["zs_tw"], df["zs_pl"] = df["o_ds_c"] / sc, df["o_ds_tw_c"] / sc, df["pl_ds_c"] / sD
    if effect:
        gap_ = an.b.terciles(df.loc[th, "zs"].to_numpy(float))[2]
        df.loc[th, "y"] = df.loc[th, "y"].to_numpy(float) + effect * df.loc[th, "zs"].to_numpy(float) / gap_
    return df


# --- CH244 worlds (7-10) ------------------------------------------------------------------------------------------------------------------------


def unrew_with_corr(rng, L: np.ndarray, r: float) -> np.ndarray:
    """World 9's statuses (1.8.1): unrewarded drawn so that the within-event correlation of ``unrew`` and ``L_j`` equals ``r`` (floor |0.20|): a latent
    ``z = a L + sqrt(1 - a^2) eps`` split at the event median, ``a = r / 0.7979`` (a median split of a standard normal correlates 0.7979 with it; LT12
    ambiguity A22); at least one of each status."""
    a = float(np.clip(r / 0.7978845608, -0.99, 0.99))
    z = a * L + math.sqrt(1.0 - a * a) * rng.standard_normal(len(L))
    u = (z > np.median(z)).astype(float)
    if u.min() == u.max():
        u[int(np.argmax(z))] = 1.0 - u[int(np.argmax(z))]
    return u


def world_ch244(world: str, rng: np.random.Generator, *, events: int = 200, effect: float = 0.0, cal: dict | None = None) -> pd.DataFrame:
    """Worlds 7-10 (1.8.1): 200 events of 3-10 members, ``n`` uniform on 8..252; member mids ``m_j + e_t + w_{j,t}`` (cents) with a common event shock
    ``e_t ~ N(0, 1.5c^2)``; spreads ``max(1, round(2 + 1.5|e_t| + AR(0.7)))`` in the same slot; statuses fixed per member (unrewarded w.p. 0.5, at least one of
    each); every member a latent liquidity ``L_j ~ N(0, 1)`` seen as ``L_j + N(0, 0.5^2)`` (``lowliq`` within event; world 9's tiers at its quartiles; LT12
    ambiguity A23: worlds 7, 8 and 10 carry ``L_j`` without any effect so that the point condition can be evaluated). World 8: every move on the favourite,
    longshots static up to noise with spreads AR(0.8) around 3c, the favourite rewarded w.p. 0.8, the longshots 0.4. World 9: ``E[ds] = 0.8c exp(-0.7 L_j)
    shock`` and the census status-liquidity correlation. World 10: a per-event drift ``mu_t`` (AR 0.99, SD 0.5c; drawn per event, code-freeze check fix 1) entering the unrewarded members' targets and, at 0.3
    per SD, the shock propensity (the event shock's scale ``exp(0.3 mu_t / 0.5)``, at k and at k + 3 alike). ``effect`` = cents on ``shock x unrew``."""
    cal = cal or {}
    r9 = cal.get("world9_corr", DEV_CAL["world9_corr"])
    r9 = math.copysign(max(abs(float(r9)), 0.20), float(r9) if float(r9) != 0 else -1.0)
    parts = []
    for e in range(events):
        M = int(rng.integers(3, 11))
        n = int(rng.integers(8, SLOTS + 1))  # re-check fix 2: n uniform on 8..252 (worlds 7-10), so events with n_e < 16 occur
        st = _place(rng, n)
        # code-freeze check fix 1: world 10's slow drift is drawn per EVENT (1.8 table "a slow event drift"; LT11 world 13's form); drawn only in world 10
        mu = ar1(rng, (n,), MQ_RHO, MQ_SD) if world == "10" else None
        scale = np.exp(MQ_LOADING * mu / MQ_SD) if world == "10" else np.ones(n)
        et = rng.normal(0.0, 1.5, n) * scale
        mj = np.sort(rng.uniform(5.0, 60.0, M))[::-1]
        w = rng.normal(0.0, 0.5, (M, n))
        if world == "8":
            mid = np.vstack([mj[0] + et + w[0], mj[1:, None] + rng.normal(0.0, 0.2, (M - 1, n))])
            s = np.vstack([floor_round(2.0 + 1.5 * np.abs(et) + ar1(rng, (n,), 0.7, 1.0)), floor_round(3.0 + ar1(rng, (M - 1, n), 0.8, 1.0))])
            pr = np.r_[0.8, np.full(M - 1, 0.4)]
            rew = (rng.random(M) < pr).astype(float)
            if rew.min() == rew.max():
                rew[int(rng.integers(0, M))] = 1.0 - rew[0]
            unrew = 1.0 - rew
        else:
            mid = mj[:, None] + et[None, :] + w
            s = floor_round(2.0 + 1.5 * np.abs(et)[None, :] + ar1(rng, (M, n), 0.7, 1.0))
            L0 = rng.normal(0.0, 1.0, M)
            if world == "9":
                unrew = unrew_with_corr(rng, L0, r9)
            else:
                unrew = (rng.random(M) < 0.5).astype(float)
                if unrew.min() == unrew.max():
                    unrew[int(rng.integers(0, M))] = 1.0 - unrew[0]
        L = L0 if world != "8" else rng.normal(0.0, 1.0, M)
        d = np.diff(mid, axis=1, prepend=mid[:, :1])
        a = np.abs(d)
        ks = np.arange(1, n - 3)
        if not len(ks):
            continue
        oth = np.stack([np.max(np.delete(a, i, axis=0), axis=0) for i in range(M)])
        shock = (oth >= 2.0 - 1e-9).astype(float)
        ssize = np.minimum(oth, 20.0)
        rank = np.argsort(np.argsort(-mid, axis=0), axis=0) + 1
        for i in range(M):
            proxy = L[i] + rng.normal(0.0, 0.5, len(ks))
            y = s[i, ks + 1] - s[i, ks]
            if world == "9":
                y = y + 0.8 * math.exp(-0.7 * L[i]) * shock[i, ks]
            if world == "10" and unrew[i] == 1:
                y = y + mu[ks + 1]
            parts.append(pd.DataFrame({"event_id": f"e{e}", "nrkey": f"e{e}", "market_id": f"e{e}-{i}", "slot": st + ks, "unrew": unrew[i], "shock": shock[i, ks],
                                       "shock_size_raw": ssize[i, ks], "d": d[i, ks], "absd": a[i, ks], "own_ds_c": s[i, ks] - s[i, ks - 1], "spread_c": s[i, ks],
                                       "spread_k_c": s[i, ks], "n_members": float(M), "fav": (rank[i, ks - 1] == 1).astype(float), "liq_proxy": proxy, "L": L[i], "y": y,
                                       "shock_tw": shock[i, ks + 3], "fam": str(e % FAMILIES)}))
    df = pd.concat(parts, ignore_index=True)
    df = _finish(df)
    df["line"] = "member"
    med = df.groupby(["event_id", "slot"])["liq_proxy"].transform("median").to_numpy(float)
    df["lowliq"] = (df["liq_proxy"].to_numpy(float) < med - 1e-12).astype(float)
    if world == "9":
        q = np.quantile(df["liq_proxy"].to_numpy(float), [0.25, 0.5, 0.75])
        tier = np.searchsorted(q, df["liq_proxy"].to_numpy(float), side="right")
        for t_ in (1, 2, 3):
            df[f"tl{t_}"] = (tier == t_).astype(float)
    sc = float(np.std(df["shock_size_raw"].to_numpy(float))) or 1.0
    df["shock_sz"] = df["shock_size_raw"] / sc
    lt._recompute("CH244", df)
    df["shock_x_unrew_tw"] = df["shock_tw"] * df["unrew"]
    if effect:
        df["y"] = df["y"] + effect * df["shock_x_unrew"]
    return _remove(df, rng)


# --- generation, controls, evaluation -------------------------------------------------------------------------------------------------------------


CTRL = {"CH245": ["own_ds_c", "o_spread_km1_c", "spread_c"],
        "CH244": ["unrew", "shock", "shock_sz", "d", "absd", "own_ds_c", "spread_c", "n_members", "fav"]}
EXTRA_CTRL = {"1": ("rv_proxy",), "2": ("rv_proxy",), "3": ("rv_proxy", *(f"sd{s_}" for s_ in range(1, 12))), "5": ("liq_proxy",),
              "9": ("tl1", "tl2", "tl3", "tl1_x_shock", "tl2_x_shock", "tl3_x_shock")}


def generate(world: str, rng: np.random.Generator, *, effect: float = 0.0, small: bool = False, cal: dict | None = None, cross: float = 0.0) -> tuple[pd.DataFrame, str]:
    test = SCENARIOS[world]["test"] if world in SCENARIOS else "CH245"
    if test == "CH245":
        return world_ch245(world, rng, events=40 if small else 300, effect=effect, cal=cal, cross=cross), test
    return world_ch244(world, rng, events=25 if small else 200, effect=effect, cal=cal), test


def _controls(test: str, world: str, df: pd.DataFrame) -> list[str]:
    c = [x for x in CTRL[test] if x in df]
    return c + [x for x in EXTRA_CTRL.get(world, ()) if x in df and x not in c]


def evaluate_world(world: str, sub_seed: int, spec: dict, *, stat: str, draws: int, effect: float = 0.0, small: bool = False, cal: dict | None = None) -> dict:
    """One world under its binding test: the gate rejection (the analysis' own gate path: ``analysis.gate``) or the verdict-size statistic (analytic p < 0.05
    AND F and every point condition hold; the gate is omitted)."""
    rng = np.random.default_rng(sub_seed)
    df, test = generate(world, rng, effect=effect, small=small, cal=cal)
    P = df[df["line"] == "thin"].reset_index(drop=True) if test == "CH245" else df
    ctrl = [c for c in _controls(test, world, P) if np.nanstd(P[c].to_numpy(float)) > 0]
    y = P["y"].to_numpy(float)
    seed = int(sub_seed % (2**31 - 1))
    rec: dict = {"n": int(len(P))}
    if stat == "gate":
        g = an.gate(P, y, test, ctrl, spec, draws=draws, seed=seed)  # re-check fix 1: the analysis' own gate path (gate sample n_e >= 16, refitted CR1 t)
        rec.update(gate_testable=bool(g.get("testable")), reject=bool(g.get("passes")), excluded_events=g.get("excluded_events"), omitted_share_max=g.get("omitted_share_max"))
        return rec
    r = an.fit12(P, y, lt.TERM[test], ctrl, seed=seed, n_boot=20)
    if not r.get("testable"):
        return {**rec, "reject": False, "testable": False}
    f = an.f_rule(P, y, test, ctrl, r, spec, n_boot=20)
    pc = an.point_conditions(df, P, test, ctrl, r, spec, n_boot=20)
    cond = bool(f.get("available") and f.get("holds") and pc.get("holds"))
    rec.update(p_analytic=float(r["p"]), analytic_reject=bool(r["p"] < 0.05), reject=bool(r["p"] < 0.05 and cond), f_holds=bool(f.get("holds", False)), point_holds=bool(pc.get("holds", False)))
    return rec


def census_cal(spec: dict, *, dev: bool) -> tuple[dict, str]:
    """The census inputs of the worlds (7): ``rho_census`` (world 1), the receipt-gap q50 / q90 (world 2), the status-liquidity correlation (world 9). A
    registered run refuses while any is unfilled (``rho_census`` may be NaN: world 1 then fails by its rule); development and timing runs use the labelled
    placeholders of ``DEV_CAL``."""
    cf = spec.get("census_fixed") or {}
    c45, c44 = cf.get("CH245") or {}, cf.get("CH244") or {}
    vals = {"rho_census": c45.get("rho_census"), "rgap_q50_s": c45.get("rgap_q50_s"), "rgap_q90_s": c45.get("rgap_q90_s"), "world9_corr": c44.get("world9_corr")}
    filled = all(v is not None for k_, v in vals.items() if k_ != "rho_census") and (vals["rho_census"] is not None or c45.get("rho_census_nan") is True)
    if filled:
        return vals, "census_fixed"
    if not dev:
        raise Refused(f"census_fixed values of the worlds are unfilled: {sorted(k_ for k_, v in vals.items() if v is None)}")
    return dict(DEV_CAL), "development placeholders (census_fixed unfilled; not a size result)"


def size_check(*, worlds: int, draws: int, seed: int, spec: dict, tests=None, scenarios=SCENARIO_ORDER, power_worlds: int | None = None, r1_worlds: int | None = None,
               small: bool = False, registered: bool = False, cal: dict | None = None, progress=None) -> dict:
    """``worlds`` worlds per scenario (one generator seeded ``seed``; the sub-seeds drawn in table order), each under its binding test and statistic (1.8).
    Criterion: the frozen 0.058 at 2,000 worlds. World 1's ``lambda`` comes from :func:`world1_lambda` first; on its failure worlds 1 and 3 are not run and
    CH245 is 'SE check failed (size scenario)'. Reported, non-binding: the power runs and world R1. A failing gate scenario sets only its test to 'SE check
    failed (size scenario)', a failing verdict-size scenario to '(mechanical world)'; k unchanged; no rerun, reseed or redesign."""
    seed_guard(seed, registered=registered)
    if registered and cal is None:
        raise Refused("the registered size check needs the census-fixed world inputs (cal); development placeholders are never a size result")
    unknown = [s for s in scenarios if s not in SCENARIOS]
    if unknown:
        raise Refused(f"unknown size scenario {unknown}")
    cal = dict(cal or DEV_CAL)
    lam = world1_lambda(cal.get("rho_census"), spec, seed=derived_seed(seed, 61))
    cal["lambda"] = lam.get("lambda")
    lim = limit_for(worlds)
    alive = list(tests) if tests is not None else list(TESTS)
    master = np.random.default_rng(seed)
    res: dict = {t: {} for t in alive}
    for sc in scenarios:
        sp = SCENARIOS[sc]
        if sp["test"] not in alive:
            continue
        if sc in ("1", "3") and not lam["ok"]:
            for _ in range(worlds):
                master.integers(1, 2**62)  # the sub-seed sequence of the later scenarios is unchanged by the failure
            res[sp["test"]][sc] = {"scenario": sc, "stat": sp["stat"], "worlds": 0, "not_run": True, "reason": f"world 1 loading failed: {lam.get('reason')}", "ok": False}
            continue
        k = n = ka = nu = 0
        for i in range(worlds):
            sub = int(master.integers(1, 2**62))
            r = evaluate_world(sc, sub, spec, stat=sp["stat"], draws=draws, small=small, cal=cal)
            n += 1
            k += int(r.get("reject", False))
            ka += int(r.get("analytic_reject", False))
            nu += int(not r.get("gate_testable", True) if sp["stat"] == "gate" else not r.get("testable", True))
            if progress:
                progress(sc, i + 1, worlds)
        rate = k / n if n else float("nan")
        rec = {"scenario": sc, "stat": sp["stat"], "worlds": n, "rejections": k, "rate": rate, "limit": lim, "ok": bool(n == worlds and rate <= lim),
               "untestable": nu}  # code-freeze check fix 4: worlds whose gate (or verdict fit) was untestable, counted as non-rejections and reported
        if sp["stat"] == "verdict":  # code-freeze check fix 3: the analytic p's own rejection rate (worlds 6, 10) feeds 'analytic p oversized in simulation'
            arate = ka / n if n else float("nan")
            rec.update(analytic_rejections=ka, analytic_rate=arate, analytic_over_limit=bool(n and arate > lim))
        res[sp["test"]][sc] = rec
    per_test = {}
    for t in alive:
        fs, fm, miss, over, unt = [], [], [], [], {}
        for sc in (SCENARIO_ORDER if registered else scenarios):
            if SCENARIOS[sc]["test"] != t:
                continue
            r = res[t].get(sc)
            if r is None or (r["worlds"] != worlds and not r.get("not_run")):
                miss.append(sc)
            elif not r["ok"]:
                (fs if SCENARIOS[sc]["stat"] == "gate" else fm).append(sc)
            if r is not None and r.get("analytic_over_limit"):
                over.append(sc)
            if r is not None and r.get("untestable"):
                unt[sc] = r["untestable"]
        # code-freeze check fix 3 (LT12 A40): 'analytic p oversized in simulation' = the analytic p's own rejection rate in the verdict-size world (6 or 10)
        # exceeds the frozen limit (1.8: 0.058 at 2,000 worlds); a label only, never a verdict or a size status
        per_test[t] = {"status": "fail_size_scenario" if (fs or miss) else ("fail_mechanical_world" if fm else "pass"), "failed_size": fs, "failed_mechanical": fm, "missing": miss,
                       "analytic_oversized": bool(over), "analytic_over_in": over, "untestable_worlds": unt}
    out = {"worlds": worlds, "draws": draws, "seed": seed, "limit": lim, "scenarios": res, "per_test": per_test, "seed_kind": "registered" if registered else "development",
           "world1_lambda": lam, "census_inputs_used": {k_: v for k_, v in cal.items() if k_ != "lambda"}}
    if power_worlds:
        out["power_runs"] = {}
        for t in alive:
            first, eff, label = {"CH245": ("1", 1.0, "1.0c per tercile gap of zs_D"), "CH244": ("7", 1.0, "1.0c between classes on shock captures")}[t]
            if first == "1" and not lam["ok"]:
                out["power_runs"][t] = {"effect": label, "not_run": True, "reason": "world 1 loading failed", "binding": False}
                continue
            g = np.random.default_rng(derived_seed(seed, {"CH245": 51, "CH244": 52}[t]))
            hit = sum(int(evaluate_world(first, int(g.integers(1, 2**62)), spec, stat="gate", draws=draws, effect=eff, small=small, cal=cal).get("reject", False)) for _ in range(power_worlds))
            out["power_runs"][t] = {"effect": label, "worlds": power_worlds, "gate_power": hit / power_worlds, "binding": False}
    if r1_worlds and "CH245" in alive:
        out["world_R1"] = world_r1(r1_worlds, spec, small=small, seed=derived_seed(seed, 54))
    return out


def world_r1(worlds: int, spec: dict, *, seed: int, small: bool = False) -> dict:
    """World R1 (1.8, R1 should-fix 1; a printed diagnostic of the binding both-sets rule, not a size criterion): world 4's pairs with each book's next spread
    change loading 0.4 per SD on the other book's innovation in BOTH directions and the 1c floor on both books; the share of worlds in which ``beta_dense <
    0.5 x beta_thin`` holds on the full set, on the dense ``spread_k >= 2`` ticks set, and on both together."""
    g = np.random.default_rng(seed)
    ratio = float(spec["verdict"]["point_condition_ratio"])
    full = ge2 = both = 0
    n_done = 0
    for _ in range(worlds):
        rng = np.random.default_rng(int(g.integers(1, 2**62)))
        df = world_ch245("4", rng, events=40 if small else 300, cal={}, cross=R1_LOADING)
        P = df[df["line"] == "thin"].reset_index(drop=True)
        ctrl = [c for c in CTRL["CH245"] if np.nanstd(P[c].to_numpy(float)) > 0]
        r = an.fit12(P, P["y"].to_numpy(float), "zs", ctrl, seed=1, n_boot=20)
        if not r.get("testable"):
            continue
        Dn = df[df["line"] == "dense"].reset_index(drop=True)
        rd = an.fit12(Dn, Dn["y"].to_numpy(float), "zs", ctrl, seed=1, n_boot=20)
        P2 = P[P["o_spread_k_ticks"] >= 2.0].reset_index(drop=True)
        D2 = Dn[Dn["own_spread_k_ticks"] >= 2.0].reset_index(drop=True)
        r2 = an.fit12(P2, P2["y"].to_numpy(float), "zs", ctrl, seed=1, n_boot=20)
        rd2 = an.fit12(D2, D2["y"].to_numpy(float), "zs", ctrl, seed=1, n_boot=20)
        a = an._pc(rd.get("beta"), r.get("beta"), ratio)
        c = an._pc(rd2.get("beta"), r2.get("beta"), ratio)
        full, ge2, both, n_done = full + int(a), ge2 + int(c), both + int(a and c), n_done + 1
    return {"worlds": n_done, "loading": R1_LOADING, "seed": seed, "share_full_set": full / n_done if n_done else float("nan"),
            "share_ge2_ticks_set": ge2 / n_done if n_done else float("nan"), "share_both": both / n_done if n_done else float("nan"), "binding": False}


# --- size-check timing (8.4 step 3): the clock only ----------------------------------------------------------------------------------------------


TIMING_KEYS = frozenset({"purpose", "seed", "seed_kind", "worlds_per_scenario", "draws", "seconds_per_world", "seconds_total", "projection", "cal_source", "code_sha256",
                         "spec_sha256", "design_text_sha256", "host", "started_utc", "finished_utc"})
PLANNED_CENSUS_COMMIT = "2026-11-19T00:00:00Z"  # 8.4 timetable: census 11-18..11-19
DRY_RUN_ALLOWANCE_H = 24.0  # LT12 ambiguity A24: 8.4 step 3 names the dry run without a duration; one day is allowed for it
FAST_LANE_LIMIT = "2026-12-08T00:00:00Z"


def size_timing(*, spec: dict, worlds: int = 20, draws: int = 200, seed: int = TIMING_SEED, small: bool = False, clock=None) -> dict:
    """8.4 step 3: the wall-clock seconds per world of each of the 10 scenarios (and of world R1) at a timing seed (never 20261597, never the development
    seed), projected to 2,000 worlds x 200 draws plus 2 x 500 power-run worlds and 500 R1 worlds. ONLY the clock is kept: each world's return value is dropped
    unread, and the output holds no rejection, rate, p-value, status or any other result of the worlds."""
    import time as _time

    if seed in REGISTERED_SEEDS or seed == DEV_SEED:
        raise Refused("the timing run needs a seed other than 20261597, its registered derived seeds (power, R1, calibration) and the development seed (8.4 step 3)")
    if worlds < 1 or draws < 1:
        raise Refused("worlds / draws too small")
    clock = clock or _time.perf_counter
    cal, src = dict(DEV_CAL), "development placeholders (timing only)"
    t0 = clock()
    lam = world1_lambda(cal["rho_census"], spec, seed=derived_seed(seed, 61))
    t_lambda = clock() - t0
    cal["lambda"] = lam.get("lambda") if lam.get("ok") else 1.0  # timing only: a fixed loading if the placeholder calibration fails
    master = np.random.default_rng(seed)
    per: dict[str, float] = {}
    for sc in SCENARIO_ORDER:
        stat = SCENARIOS[sc]["stat"]
        t0 = clock()
        for _ in range(worlds):
            evaluate_world(sc, int(master.integers(1, 2**62)), spec, stat=stat, draws=draws, small=small, cal=cal)  # return value deliberately discarded (clock only)
        per[sc] = (clock() - t0) / worlds
    t0 = clock()
    world_r1(min(worlds, 5), spec, small=small, seed=derived_seed(seed, 54))  # discarded (clock only)
    per["R1"] = (clock() - t0) / min(worlds, 5)
    sc_cfg = spec["size_check"]
    W, D, PW, RW = int(sc_cfg["worlds"]), int(sc_cfg["draws"]), int(sc_cfg["power_worlds"]), int(sc_cfg["r1_worlds"])
    f_draw = D / draws
    proj_sc = {sc: per[sc] * W * (f_draw if SCENARIOS[sc]["stat"] == "gate" else 1.0) for sc in SCENARIO_ORDER}
    proj_pw = (per["1"] + per["7"]) * PW * f_draw
    proj_r1 = per["R1"] * RW
    total_s = sum(proj_sc.values()) + proj_pw + proj_r1 + t_lambda
    end = lt.epoch(PLANNED_CENSUS_COMMIT) + total_s + 24 * 3600.0 + DRY_RUN_ALLOWANCE_H * 3600.0
    return {"purpose": "LT12 size-check timing (LIVE_TESTS_12.md 8.4 step 3): wall-clock only; no result of these worlds is recorded", "seed": seed, "seed_kind": "timing",
            "worlds_per_scenario": worlds, "draws": draws, "seconds_per_world": per, "seconds_total": float(sum(v for k_, v in per.items() if k_ != "R1") * worlds), "cal_source": src,
            "projection": {"worlds": W, "draws": D, "power_worlds": PW, "r1_worlds": RW, "draw_scaling": "linear in draws (gate scenarios)", "seconds_by_scenario": proj_sc,
                           "power_run_seconds": proj_pw, "r1_seconds": proj_r1, "lambda_seconds": t_lambda, "total_seconds": total_s, "total_hours": total_s / 3600.0,
                           "planned_census_commit_utc": PLANNED_CENSUS_COMMIT, "margin_h": 24, "dry_run_allowance_h": DRY_RUN_ALLOWANCE_H, "projected_end_utc": lt.iso(end),
                           "fast_lane_limit_utc": FAST_LANE_LIMIT, "ordered_lane_ledger_line_needed": bool(end > lt.epoch(FAST_LANE_LIMIT))}}


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
    if not args.dev and (args.worlds is not None or args.draws is not None):
        print("refusing: --worlds / --draws need --dev (the registered size check is 2,000 worlds x 200 draws, seed 20261597)")
        return 2
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
        for t in tests:
            if (m := lt.census_fixed_missing(spec, t)):
                print(f"refusing: census_fixed.{t} has unfilled values {m}")
                return 2
    if int(spec["seeds"]["size_check"]) != REGISTERED_SEED:
        print("refusing: the spec's size-check seed is not 20261597")
        return 2
    try:
        cal, src = census_cal(spec, dev=bool(args.dev))
    except Refused as exc:
        print(f"refusing: {exc}")
        return 2
    out = size_check(worlds=worlds, draws=draws, seed=REGISTERED_SEED if not args.dev else DEV_SEED, spec=spec, tests=list(tests) if tests else None, registered=not args.dev,
                     power_worlds=int(sc["power_worlds"]) if not args.dev else int(getattr(args, "power_worlds", 0) or 0), r1_worlds=int(sc["r1_worlds"]) if not args.dev else 0, cal=cal)
    out.update(code_sha256=lt.code_hashes(), spec_sha256=spec["_sha256"], design_text_sha256=lt.design_text_sha(), dev=bool(args.dev), cal_source=src)
    return write_out(args.out, json.dumps(bd._clean(out), sort_keys=True, indent=1, default=str))
