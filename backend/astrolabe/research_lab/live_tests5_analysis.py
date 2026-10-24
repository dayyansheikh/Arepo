# ruff: noqa: E501
"""LT5 analysis module (docs/research_lab/LIVE_TESTS_5.md). DRAFT. This unit holds the gates and the simulated-null size
check (sections 1.8 and 1.8.1); the single analysis is written in a later unit.

* ``fl_perm_gate`` (vendored, LT4): Freedman-Lane permutation of the reduced-model residuals within strata (J, F, H, R).
* ``block_fl_gate``: O's gate (R1 finding 1; re-check finding 1). Within each market the reduced-model residual series,
  ordered by origin, is circularly shifted by an offset drawn uniformly from ``[s_m, n_m - s_m]`` with
  ``s_m = max(4, ceil(n_m / 4))``; markets with ``n_m < 16`` keep their residuals in place (excluded from the
  comparison); the full model is refitted.
* ``size_check``: the twelve binding scenarios of 1.8, worlds exactly as declared in 1.8.1, one generator seeded once.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import live_tests5 as lt
from . import live_tests5_base as b

fl_perm_gate = b.fl_perm_gate


# --- O's block (circular-shift) Freedman-Lane gate ---------------------------------------------------------------------


def shift_plan(codes: np.ndarray, order: np.ndarray, min_n: int) -> list[np.ndarray]:
    """Row indices of each market with >= ``min_n`` rows, sorted by ``order`` (the markets the gate shifts)."""
    out = []
    for c in np.unique(codes):
        idx = np.flatnonzero(codes == c)
        if len(idx) >= min_n:
            out.append(idx[np.argsort(order[idx], kind="mergesort")])
    return out


def offset_range(n: int) -> tuple[int, int]:
    s = max(4, math.ceil(n / 4))
    return s, n - s


def circular_shift(e: np.ndarray, plan: list[np.ndarray], rng: np.random.Generator) -> np.ndarray:
    """One draw: each planned market's residuals rotated by its own uniform offset; other rows unchanged."""
    ep = e.copy()
    for idx in plan:
        lo, hi = offset_range(len(idx))
        ep[idx] = np.roll(e[idx], int(rng.integers(lo, hi + 1)))
    return ep


def block_fl_gate(df: pd.DataFrame, y: np.ndarray, term: str, controls: list[str], *, sign: int, draws: int, seed: int,
                  min_n: int = 16, group: str = "market_id", order: str = "t_row") -> dict:
    """O's gate: as ``fl_perm_gate`` (same demeaning, same reduced-model residuals and statistic), but the null draws
    rotate each market's residual series instead of permuting residuals within strata. p_perm = (1 + #{sign * draw >=
    sign * real}) / (1 + draws) < 0.05 passes."""
    X = b.demean(df, [term, *controls], group, order, "expanding")
    yv = np.asarray(y, float)
    ok = np.isfinite(yv) & np.all(np.isfinite(X.to_numpy()), axis=1)
    if ok.sum() < 10:
        return {"testable": False, "passes": False, "reason": "fewer than 10 rows"}
    Z = X[controls].to_numpy()[ok] if controls else np.zeros((int(ok.sum()), 0))
    xt = b._partial(Z, X[term].to_numpy()[ok])
    e = b._partial(Z, yv[ok])
    sxx = float(xt @ xt)
    if sxx <= 1e-18:
        return {"testable": False, "passes": False, "reason": "no residual variation in the term"}
    real = float(xt @ e / sxx)
    codes = pd.factorize(df[group].astype(str).to_numpy()[ok])[0]
    plan = shift_plan(codes, df[order].to_numpy(float)[ok], min_n)
    shifted = int(sum(len(i) for i in plan))
    if not plan:
        return {"testable": False, "passes": False, "reason": f"no market with >= {min_n} rows", "share_rows_shifted": 0.0}
    rng = np.random.default_rng(seed)
    ge = 0
    for _ in range(draws):
        bb = float(xt @ circular_shift(e, plan, rng) / sxx)
        ge += int(sign * bb >= sign * real)
    p = (1 + ge) / (1 + draws)
    return {"testable": True, "real": real, "p_perm": p, "passes": bool(p < 0.05), "draws": draws,
            "method": "block circular-shift Freedman-Lane", "min_n": min_n, "share_rows_shifted": shifted / int(ok.sum()),
            "markets_shifted": len(plan)}


# --- simulated worlds (LIVE_TESTS_5.md 1.8.1; no effect of the tested term in any world) ----------------------------------


def _n_m(rng: np.random.Generator, lo: int = 6, hi: int = 60) -> int:
    return int(rng.integers(lo, hi + 1))


def _ar(rng: np.random.Generator, n: int, rho: float) -> np.ndarray:
    """AR(1) with stationary SD 1 (rho 0 gives iid N(0, 1))."""
    v = np.empty(n)
    v[0] = rng.normal()
    s = math.sqrt(1.0 - rho**2)
    for i in range(1, n):
        v[i] = rho * v[i - 1] + s * rng.normal()
    return v


def sim_markov_ma2_world(rng: np.random.Generator, *, n_mkt: int = 60, persistence: float = 0.6) -> tuple[pd.DataFrame, np.ndarray]:
    """Scenario 4 (J): unbalanced markets (n_m uniform 6..60); label rate U(0.15, 0.6), kept with probability
    ``persistence`` else redrawn; target level + u_{i+1} + u_{i+2} + 0.5 u_{i+3}, u ~ N(0, 0.03); c1 ~ N(0, 1), no effect."""
    rows = []
    for m in range(n_mkt):
        n = _n_m(rng)
        pr, lvl = rng.uniform(0.15, 0.6), rng.normal(0, 0.01)
        u = rng.normal(0, 0.03, n + 3)
        lab = int(rng.random() < pr)
        for i in range(n):
            lab = lab if rng.random() < persistence else int(rng.random() < pr)
            rows.append({"market_id": f"m{m}", "event_id": f"e{m // 3}", "t_row": i * 7200.0, "day": str(i // 12), "P": lab,
                         "c1": rng.normal(), "y": lvl + u[i + 1] + u[i + 2] + 0.5 * u[i + 3]})
    df = pd.DataFrame(rows)
    return df, df["y"].to_numpy(float)


def sim_h_world(rng: np.random.Generator, *, n_mkt: int = 120, persistence: float = 0.6) -> tuple[pd.DataFrame, np.ndarray]:
    """Scenarios 5-6 (H): one unit per market per day, n_m days uniform 4..21; label rate U(0.1, 0.4), kept with
    probability ``persistence`` per day else redrawn; daily target = level + sum of 12 pass shocks N(0, 0.0173);
    control c1 = 0.5 zL + sqrt(0.75) xi with a real effect 0.02."""
    rows = []
    for m in range(n_mkt):
        n = _n_m(rng, 4, 21)
        pr, lvl = rng.uniform(0.1, 0.4), rng.normal(0, 0.01)
        sd_l = math.sqrt(pr * (1 - pr))
        lab = int(rng.random() < pr)
        for d in range(n):
            lab = lab if rng.random() < persistence else int(rng.random() < pr)
            c1 = 0.5 * (lab - pr) / sd_l + math.sqrt(0.75) * rng.normal()
            y = lvl + float(rng.normal(0, 0.0173, 12).sum()) + 0.02 * c1
            rows.append({"market_id": f"m{m}", "event_id": f"e{m // 3}", "t_row": d * 86400.0, "day": str(d), "L": lab, "c1": c1, "y": y})
    df = pd.DataFrame(rows)
    return df, df["y"].to_numpy(float)


R_TERMS = ["imb", "imb_x_inside", "imb_x_rf", "imb_x_rf_x_inside", "inside", "rf", "rf_x_inside"]


def sim_r_world(rng: np.random.Generator, *, n_mkt: int = 100, rho: float = 0.6) -> tuple[pd.DataFrame, np.ndarray]:
    """Scenarios 7-8 (R): n_m uniform 6..60; folded mid f = clip(f0 + d, 0.840, 0.959), f0 ~ U(0.845, 0.955), d AR(1)
    rho 0.95 with stationary SD 0.015 (inside near-constant within most markets); imb = N(0, 0.3) market level + AR(1)
    ``rho`` (stationary SD 1); y = level + 0.01 imb + 0.005 inside + 0.1 rf + N(0, 0.035); no slope jump."""
    rows = []
    for m in range(n_mkt):
        n = _n_m(rng)
        f0, lvl, il = rng.uniform(0.845, 0.955), rng.normal(0, 0.01), rng.normal(0, 0.3)
        d = 0.015 * _ar(rng, n, 0.95)
        im = il + _ar(rng, n, rho)
        for i in range(n):
            f = min(max(f0 + d[i], 0.840), 0.959)
            rf, ins = f - 0.90, int(f <= 0.90)
            y = lvl + 0.01 * im[i] + 0.005 * ins + 0.1 * rf + rng.normal(0, 0.035)
            rows.append({"market_id": f"m{m}", "event_id": f"e{m // 3}", "t_row": i * 7200.0, "day": str(i // 12), "imb": im[i],
                         "inside": ins, "rf": rf, "imb_x_inside": im[i] * ins, "imb_x_rf": im[i] * rf, "imb_x_rf_x_inside": im[i] * rf * ins,
                         "rf_x_inside": rf * ins, "y": y})
    df = pd.DataFrame(rows)
    return df, df["y"].to_numpy(float)


def sim_o_world(rng: np.random.Generator, *, n_mkt: int = 80, rho: float = 0.0) -> tuple[pd.DataFrame, np.ndarray]:
    """Scenarios 9-12 (O): n_m uniform 6..60; z = N(0, 0.5) market level + AR(1) ``rho``; c1 = 0.85 z + sqrt(1 - 0.85^2)
    xi, xi AR(1) with the same rho; y = level + 0.02 c1 + u_{i+1} + u_{i+2} + 0.5 u_{i+3}, u ~ N(0, 0.03); no z effect."""
    rows = []
    for m in range(n_mkt):
        n = _n_m(rng)
        lvl, zl = rng.normal(0, 0.01), rng.normal(0, 0.5)
        z = zl + _ar(rng, n, rho)
        xi = _ar(rng, n, rho)
        u = rng.normal(0, 0.03, n + 3)
        for i in range(n):
            c1 = 0.85 * z[i] + math.sqrt(1 - 0.85**2) * xi[i]
            rows.append({"market_id": f"m{m}", "event_id": f"e{m // 3}", "t_row": i * 7200.0, "day": str(i // 12), "z": z[i], "c1": c1,
                         "y": lvl + 0.02 * c1 + u[i + 1] + u[i + 2] + 0.5 * u[i + 3]})
    df = pd.DataFrame(rows)
    return df, df["y"].to_numpy(float)


# --- size check ---------------------------------------------------------------------------------------------------------


def _strata_day(df: pd.DataFrame) -> np.ndarray:
    return (df["market_id"].astype(str) + "|" + df["day"].astype(str)).to_numpy()


def scenario_table(rng: np.random.Generator, draws: int) -> dict:
    """The twelve binding scenarios of LIVE_TESTS_5.md 1.8 in table order: name -> (callable returning gate passes)."""

    def fl(df, y, term, ctrl, strata) -> bool:
        return bool(fl_perm_gate(df, y, term, ctrl, sign=+1, strata=strata, draws=draws, seed=int(rng.integers(1 << 31)),
                                 min_stratum=4).get("passes"))

    def blk(df, y) -> bool:
        return bool(block_fl_gate(df, y, "z", ["c1"], sign=+1, draws=draws, seed=int(rng.integers(1 << 31)), min_n=16).get("passes"))

    def move(**kw):
        df, y = b.sim_move_world(rng, **kw)
        return fl(df, y, "P", ["c1"], _strata_day(df))

    def corr():
        df, y = b.sim_corr_label_world(rng, corr=0.7, binary=True)
        return fl(df, y, "L", ["c1"], _strata_day(df))

    def mk4():
        df, y = sim_markov_ma2_world(rng, persistence=0.6)
        return fl(df, y, "P", ["c1"], _strata_day(df))

    def h(p):
        df, y = sim_h_world(rng, persistence=p)
        return fl(df, y, "L", ["c1"], df["market_id"].astype(str).to_numpy())

    def r(rho):
        df, y = sim_r_world(rng, rho=rho)
        return fl(df, y, "imb_x_inside", [t for t in R_TERMS if t != "imb_x_inside"], _strata_day(df))

    def o(rho):
        df, y = sim_o_world(rng, rho=rho)
        return blk(df, y)

    return {"s01_fl_binary_iid": lambda: move(), "s02_fl_binary_persistent": lambda: move(persistent=True),
            "s03_fl_binary_control_corr0.7": corr, "s04_fl_markov0.6_ma2": mk4,
            "s05_fl_h_markov0.6_daily": lambda: h(0.6), "s06_fl_h_markov0.9_daily": lambda: h(0.9),
            "s07_fl_r_imb_ar0.6": lambda: r(0.6), "s08_fl_r_imb_ar0.9": lambda: r(0.9),
            "s09_block_o_rho0": lambda: o(0.0), "s10_block_o_rho0.6": lambda: o(0.6), "s11_block_o_rho0.9": lambda: o(0.9),
            "s12_block_o_rho0.95": lambda: o(0.95)}


def size_check(*, worlds: int, draws: int, seed: int, nominal: float = 0.05, binding: dict | None = None,
               only: list[str] | None = None, spec_sha256: str | None = None, dev: bool = False) -> dict:
    """Pass rate of each gate under its simulated nulls; limit nominal + 1.645 sqrt(nominal (1 - nominal) / worlds). The
    scenarios run in table order on one generator. ``binding`` maps scenario -> tests (spec ``size_check.scenarios``); a
    failing scenario sets only those tests to "SE check failed (size scenario)" (1.8). ``only`` (tests of the code) runs a
    subset and is never used for the registered statement."""
    binding = binding or lt.load_spec(sha=None)["size_check"]["scenarios"]
    rng = np.random.default_rng(seed)
    table = scenario_table(rng, draws)
    missing = [n for n in table if n not in binding or not binding[n]]
    extra = [n for n in binding if n not in table]
    if missing or extra:  # fail closed (census code check finding 6): every scenario maps to >= 1 test and vice versa
        raise ValueError(f"size-check binding map mismatch: missing {missing}, unknown {extra}")
    lim = nominal + 1.645 * float(np.sqrt(nominal * (1 - nominal) / worlds))
    out: dict = {"worlds": worlds, "draws": draws, "seed": seed, "limit": lim, "scenarios": {}, "spec_sha256": spec_sha256,
                 "dev": bool(dev or only is not None)}
    for name, fn in table.items():
        if only is not None and name not in only:
            continue
        rej = sum(int(fn()) for _ in range(worlds))
        out["scenarios"][name] = {"rate": rej / worlds, "ok": rej / worlds <= lim, "binding_for": binding[name]}
    failed = sorted({t for v in out["scenarios"].values() if not v["ok"] for t in v["binding_for"]})
    out["se_check_failed_size_scenario"] = failed
    out["all_ok"] = not failed
    out["code_sha256"] = lt.code_hashes()
    return out
