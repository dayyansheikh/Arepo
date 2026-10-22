# ruff: noqa: E501
"""LT7 (LIVE_TESTS_7.md section 7) code phase 1: every census gate on synthetic fixtures. A base population passes every gate of its
census at the DECLARED thresholds; each mutation then breaks exactly the gate it targets (and the verdict of that census with it).
``scale`` emulates a larger census (the drivers use 21 / covered days); nothing here is real data."""

from __future__ import annotations

import copy
import math

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import live_tests7 as lt

SPEC = lt.load_spec(sha=None)
SCALE = 80.0
COV = 2.0


def _ids(n_units: int, n_markets: int, per_event: int = 3):
    mk = np.repeat(np.arange(n_markets), n_units // n_markets)
    ev = np.arange(len(mk)) // per_event
    return mk, ev


def _common(rng, n: int) -> dict:
    return {"liq": np.exp(rng.normal(11, 1, n)), "tick": np.full(n, 0.01), "end_ts": np.full(n, 1.8e9), "mid": rng.uniform(0.25, 0.75, n), "sports": np.zeros(n, int)}


def _finish(u: pd.DataFrame) -> pd.DataFrame:
    u["t_row"] = u["t_row"].astype(float)
    u = lt._common_cols(u)
    return lt._anatomy(u) if "cls" in u else u


# --- CH195 -----------------------------------------------------------------------------------------------------------------------------


def pop195(*, n_m=150, per=40, rho=0.0, r_noise=1.0, h0_link=0.0, liq_link=False, tot_over=None, one_per_market=False, seed=0):
    rng = np.random.default_rng(seed)
    n = n_m * per
    mk, ev = _ids(n, n_m)
    j = np.tile(np.arange(per), n_m)
    e1, e2 = rng.normal(size=n), rng.normal(size=n)
    lvl = np.repeat(rng.normal(size=n_m), per)
    R = lvl + r_noise * e1
    R_away = np.repeat(rng.normal(size=n_m), per) + rho * e1 + math.sqrt(1 - rho * rho) * e2
    zd = R - R_away
    c = _common(rng, n)
    h0 = np.clip(0.5 + h0_link * zd / 4 + rng.normal(0, 0.1, n), 0, 1)
    if liq_link:
        c["liq"] = np.exp(11 + 1.5 * zd / zd.std())
    u = pd.DataFrame({"market_id": [f"m{m}" for m in mk], "event_id": [f"e{e}" for e in ev], "skey": [f"s{m % 20}" for m in mk], "day": "2026-10-20", "slot": j, "t_row": j * 7200.0,
                      "x": rng.choice([-1, 1], n) * rng.uniform(0.01, 0.05, n), **c, "vol24_p": np.exp(rng.normal(7, 1, n)), "spread_sw_k": rng.uniform(0.01, 0.05, n),
                      "spread_sw_p": rng.uniform(0.01, 0.05, n), "D_hit": np.expm1(R), "D_away": np.expm1(R_away), "h0": h0, "d24": rng.normal(0, 0.02, n), "d24_flag": 0.0,
                      "cls": rng.choice(["traded", "quote_only"], n), "geom": rng.choice(["parallel", "one_sided", "spread_change", "same_side_unequal"], n)})
    u["sx"] = np.sign(u["x"])
    u["R"], u["R_away"] = np.log1p(u["D_hit"]), np.log1p(u["D_away"])
    u["log_abs_x"] = np.log(np.abs(u["x"]))
    u["log1p_vol_p"] = np.log1p(u["vol24_p"])
    u["traded"] = (u["cls"] == "traded").astype(float)
    u["v_prev"] = rng.uniform(-1, 1, n)
    if one_per_market:
        u["market_id"] = [f"m{i}" for i in range(n)]
    tot = {"non_sports_ex_crypto_movers": 1000, "covered": 800, "covered_sign_agree": 700}
    tot.update(tot_over or {})
    return _finish(u), tot


@pytest.mark.parametrize("mut,fails", [
    ({}, None), ({"tot_over": {"covered": 600}}, "coverage"), ({"tot_over": {"covered_sign_agree": 500}}, "sign_agreement"),
    ({"rho": 0.95}, "corr_zR_zR_away"), ({"h0_link": 6.0}, "corr_zh0"), ({"liq_link": True}, "corr_liq"), ({"one_per_market": True}, "block_share"),
    ({"r_noise": 0.05}, "resid_iqr")])
def test_ch195_gates(mut, fails):
    U, tot = pop195(**mut)
    r = lt.census_ch195(U, tot, SPEC, SCALE, COV)
    g = r["gate_CH195"]
    if fails is None:
        assert g["pass"] is True, g
        assert r["slope"]["mde_tercile_c"] <= 0.5 and r["F"]["f_mde_c"] <= 0.5 and r["block_min_units"] == 2
    else:
        assert g[fails] is False and g["pass"] is False, g


def test_ch195_units_slope_and_f_mde_gates():
    U, tot = pop195()
    assert lt.census_ch195(U, tot, SPEC, 1.0, COV)["gate_CH195"]["units"] is False  # 6,000 projected < 42,000
    # F-MDE: a within correlation of 0.7 (below the 0.8 gate) pushes slope x sqrt(2 / (1 - r_w)) over the 0.5c cap while the slope MDE passes
    U2, tot2 = pop195(rho=0.7)
    g2 = lt.census_ch195(U2, tot2, SPEC, SCALE, COV)
    assert g2["gate_CH195"]["corr_zR_zR_away"] is True and g2["gate_CH195"]["slope_mde"] is True and g2["gate_CH195"]["f_mde"] is False and g2["F"]["f_mde_c"] > 0.5
    assert g2["F"]["declared_c"] == pytest.approx(g2["slope"]["mde_tercile_c"] * math.sqrt(2 / (1 - g2["corr_zR_zR_away"]["within"])))
    # slope MDE: the tested term nearly collinear with a control (zh0) leaves no residual variation
    U3, tot3 = pop195()
    U3["h0"] = np.clip(0.5 + 0.1 * (U3["R"] - U3["R"].mean()) / U3["R"].std() + np.random.default_rng(1).normal(0, 0.002, len(U3)), 0, 1)
    g3 = lt.census_ch195(U3, tot3, SPEC, SCALE, COV)["gate_CH195"]
    assert g3["slope_mde"] is False and g3["f_mde"] is False


def test_ch195_family_exclusion_and_min_days():
    U, tot = pop195()
    U["skey"] = np.where(np.arange(len(U)) % 10 < 5, "bigseries", U["skey"])  # one series holds 50% of the population (> 40%)
    r = lt.census_ch195(U, tot, SPEC, SCALE, COV)
    assert r["exclude_family"] == "bigseries" and r["top_family_share"] > 0.4
    assert lt.census_ch195(*pop195(), SPEC, SCALE, 1.4)["gate_CH195"]["pass"] is False  # below the 1.5-day minimum: NaN, fails
    assert lt.census_ch195(*pop195(), SPEC, SCALE, 1.5)["gate_CH195"]["pass"] is True


# --- CH191 -----------------------------------------------------------------------------------------------------------------------------


def pop191(*, n_m=200, per=40, grind=0.30, jump=0.30, cor_traded=0.0, liq_link=False, one_per_market=False, seed=0):
    rng = np.random.default_rng(seed)
    n = n_m * per
    mk, ev = _ids(n, n_m)
    j = np.tile(np.arange(per), n_m)
    cls6 = rng.choice(["grind", "jump", "other"], n, p=[grind, jump, 1 - grind - jump])
    G = (cls6 == "grind").astype(float)
    traded_last = (rng.random(n) < 0.5 + cor_traded * (G - 0.5)).astype(float)
    c = _common(rng, n)
    if liq_link:
        c["liq"] = np.exp(11 + 2.0 * G)
    u = pd.DataFrame({"market_id": [f"m{m}" for m in mk], "event_id": [f"e{e}" for e in ev], "skey": [f"s{m % 20}" for m in mk], "day": "2026-10-20", "slot": j, "t_row": j * 7200.0,
                      "x6": rng.choice([-1, 1], n) * rng.uniform(0.03, 0.08, n), "cls6": cls6, "pc": rng.uniform(0.3, 1, n), "sa": rng.uniform(0.3, 1, n),
                      "spread": rng.uniform(0.01, 0.05, n), "vol24": np.exp(rng.normal(7, 1, n)), "rv24s": np.exp(rng.normal(-5, 0.5, n)), "rv_floor": 0.0,
                      "d24": rng.normal(0, 0.02, n), "d24_flag": 0.0, "last_cls": np.where(traded_last > 0, "traded", "small_last_step"), **c})
    u["G"] = G
    u["log_abs_x6"] = np.log(np.abs(u["x6"]))
    u["log_rv24s"] = np.log(u["rv24s"])
    u["log1p_vol"] = np.log1p(u["vol24"])
    u["traded_last"] = traded_last
    for nm in ("traded", "quote_only", "ambiguous", "never_traded"):
        u[f"l_{nm}"] = (u["last_cls"] == nm).astype(float)
    if one_per_market:
        u["market_id"] = [f"m{i}" for i in range(n)]
    return _finish(u), {"movers_6h": n, "every_step_rule_loss": 10}


@pytest.mark.parametrize("mut,fails", [
    ({}, None), ({"grind": 0.10, "jump": 0.45}, "grind_share"), ({"grind": 0.45, "jump": 0.10}, "jump_share"), ({"cor_traded": 1.6}, "corr_traded_last"),
    ({"liq_link": True}, "corr_liq"), ({"one_per_market": True}, "block_share")])
def test_ch191_gates(mut, fails):
    U, tot = pop191(**mut)
    r = lt.census_ch191(U, tot, SPEC, SCALE, COV + 5)  # 7 covered days: block proxy 6 (the market has 40 units)
    g = r["gate_CH191"]
    if fails is None:
        assert g["pass"] is True, g
        assert r["mde_class_c"] <= 0.5 and r["block_min_units"] == 6
        assert r["mde_class_c"] == pytest.approx(lt.b.mde_class(r["class_eff_21d"]["grind"], r["class_eff_21d"]["jump"], 0.05, r["design_effect"]["DE_gate"], lt.mde_common(SPEC), r["design"]["vif_w"]) * 100)
    else:
        assert g[fails] is False and g["pass"] is False, g


def test_ch191_units_class_mde_and_block_proxy_scaling():
    U, tot = pop191()
    assert lt.census_ch191(U, tot, SPEC, 1.0, 7.0)["gate_CH191"]["units"] is False  # 8,000 projected < 201,600
    assert lt.census_ch191(U, tot, SPEC, 100.0, 7.0)["gate_CH191"]["units"] is True  # 800,000 projected
    g = lt.census_ch191(*pop191(grind=0.16, jump=0.16, n_m=60, per=20), SPEC, 3.0, 7.0)["gate_CH191"]  # a small, mostly 'other' population: the class MDE fails
    assert g["class_mde"] is False
    # 5 units per market: the proxy at 7 days is 6 -> fails; at 2 days it is 2 -> passes
    U5, t5 = pop191(n_m=800, per=5)
    r7, r2 = lt.census_ch191(U5, t5, SPEC, SCALE, 7.0), lt.census_ch191(U5, t5, SPEC, SCALE, 2.0)
    assert r7["block_min_units"] == 6 and r7["gate_CH191"]["block_share"] is False
    assert r2["block_min_units"] == 2 and r2["block_share"] >= 0.5 and r2["gate_CH191"]["pass"] is False and r2["gate_CH191"]["values_nan"] is True  # 2 days is below CC7's 5-day minimum


# --- CH197 -----------------------------------------------------------------------------------------------------------------------------


def pop197(*, n_m=3000, rho_imb=0.0, liq_link=False, same_day=False, one_day=False, own24_link=False, seed=0):
    rng = np.random.default_rng(seed)
    days = 1 if one_day else 2
    mk = np.repeat(np.arange(n_m), days)
    n = len(mk)
    ev = np.arange(n) // 3
    d = np.tile(np.arange(days), n_m)
    imbB = np.clip(rng.uniform(-1, 1, n), -0.99, 0.99)
    if same_day:  # day-2 imbalance equal to day 1: little change
        imbB = np.repeat(imbB[::days], days) + rng.normal(0, 0.01, n)
    imbT = np.clip(rho_imb * imbB + math.sqrt(1 - rho_imb**2) * rng.uniform(-1, 1, n), -0.99, 0.99)
    c = _common(rng, n)
    d24 = rng.normal(0, 0.02, n) + (0.05 * imbB if own24_link else 0.0)
    if liq_link:
        c["liq"] = np.exp(11 + 2.0 * imbB)
    u = pd.DataFrame({"market_id": [f"m{m}" for m in mk], "event_id": [f"e{e}" for e in ev], "skey": [f"s{m % 20}" for m in mk], "day": [f"2026-10-{20 + k}" for k in d], "slot": 6,
                      "t_row": d * 86400.0, "imbT": imbT, "imbB": imbB, "vol24": np.exp(rng.normal(7, 1, n)), "spread_sw": rng.uniform(0.01, 0.05, n),
                      "total5": np.exp(rng.normal(6, 1, n)), "h0": rng.uniform(0, 1, n), "d24": d24, "d24_flag": 0.0, "rewarded": rng.integers(0, 2, n).astype(float),
                      "in_band": rng.integers(0, 2, n).astype(float), **c})
    u["dis"] = u["imbB"] - u["imbT"]
    u["imbT1"] = np.clip(u["imbT"] * 0.8 + rng.normal(0, 0.1, n), -1, 1)
    u["log1p_total5"] = np.log1p(u["total5"])
    u["log1p_vol"] = np.log1p(u["vol24"])
    return _finish(u), {"books_in_band": int(n * 1.2)}


def pairs197(rho=0.0, n_m=150, n_pairs=8, seed=1):
    rng = np.random.default_rng(seed)
    rows = []
    for m in range(n_m):
        lvl = rng.normal() * 0.3
        for j in range(n_pairs):
            a = lvl + rng.normal()
            rows.append({"market_id": f"m{m}", "t_row": j * 7200.0, "imb_j": a, "imb_j13": lvl + rho * (a - lvl) + math.sqrt(1 - rho**2) * rng.normal()})
    return pd.DataFrame(rows)


@pytest.mark.parametrize("mut,fails", [
    ({}, None), ({"rho_imb": 0.9}, "corr_imbT_imbB"), ({"same_day": True}, "day_diff_share"), ({"one_day": True}, "market_strata"), ({"liq_link": True}, "corr_liq"),
    ({"own24_link": True}, "corr_own24")])
def test_ch197_gates(mut, fails):
    U, tot = pop197(**mut)
    r = lt.census_ch197(U, tot, SPEC, SCALE, COV, pairs197())
    g = r["gate_CH197"]
    if fails is None:
        assert g["pass"] is True, g
        assert r["slope"]["mde_tercile_c"] <= 0.5 and r["F"]["f_mde_c"] <= 0.5 and r["F"]["design_c"] is None
    else:
        assert g[fails] is False and g["pass"] is False, g


def test_ch197_units_covered_share_r_gate_and_f_mde():
    U, tot = pop197()
    assert lt.census_ch197(U, tot, SPEC, 1.0, COV, pairs197())["gate_CH197"]["units"] is False
    low = lt.census_ch197(U, {"books_in_band": len(U) * 3}, SPEC, SCALE, COV, pairs197())["gate_CH197"]
    assert low["covered_share"] is False  # 33% < 60%
    # r_gate = max(r_w, r_pool) over the pairs; both printed; > 0.8 fails the cap, and r_gate drives the F-MDE
    hi = lt.census_ch197(U, tot, SPEC, SCALE, COV, pairs197(rho=0.95))
    assert hi["pairs"]["r_gate"] > 0.8 and hi["gate_CH197"]["r_gate"] is False and hi["gate_CH197"]["f_mde"] is False
    assert {"r_w", "r_pool", "r_gate"} <= set(hi["pairs"]) and hi["pairs"]["r_gate"] == max(hi["pairs"]["r_w"], hi["pairs"]["r_pool"])
    mid = lt.census_ch197(U, tot, SPEC, SCALE, COV, pairs197(rho=0.6))
    assert mid["F"]["f_mde_c"] == pytest.approx(mid["slope"]["mde_tercile_c"] * math.sqrt(2.0 / (1.0 - max(0.0, mid["pairs"]["r_gate"]))))
    assert mid["gate_CH197"]["f_mde"] is False and mid["gate_CH197"]["slope_mde"] is True  # 0.5c cap on the F-MDE
    # the pooled correlation carries the market level: r_pool above r_w makes r_gate the pooled one
    lvl_pairs = pairs197(rho=0.0)
    lvl_pairs["imb_j"] += np.repeat(np.random.default_rng(2).normal(size=150) * 2, 8)
    lvl_pairs["imb_j13"] += np.repeat(lvl_pairs.groupby("market_id")["imb_j"].transform("mean").to_numpy()[::8] * 0.9, 8)
    rr = lt.census_ch197(U, tot, SPEC, SCALE, COV, lvl_pairs)["pairs"]
    assert rr["r_pool"] > rr["r_w"] and rr["r_gate"] == rr["r_pool"]
    nan_pairs = lt.census_ch197(U, tot, SPEC, SCALE, COV, pairs197().iloc[0:0])
    assert nan_pairs["gate_CH197"]["r_gate"] is False and nan_pairs["gate_CH197"]["f_mde"] is False  # no pairs: NaN fails
    assert lt.census_ch197(U, tot, SPEC, SCALE, 1.9, pairs197())["gate_CH197"]["pass"] is False  # both 12:31Z passes needed (minimum covered days 2)


# --- CH193 -----------------------------------------------------------------------------------------------------------------------------


def pop193(*, n_m=200, per=40, lag_rho=0.0, vol_link=0.0, rv_link=0.0, liq_link=False, narrow=False, one_per_market=False, seed=0):
    rng = np.random.default_rng(seed)
    n = n_m * per
    mk, ev = _ids(n, n_m)
    j = np.tile(np.arange(per), n_m)
    e1, e2 = rng.normal(size=n), rng.normal(size=n)
    lvl = np.repeat(rng.normal(size=n_m), per)
    ldv = (0.0 if narrow else 1.0) * (lvl + e1) + 2.0 + (0.0 if not narrow else 0.01 * e1)
    ldv_lag = lag_rho * e1 + math.sqrt(1 - lag_rho**2) * e2 + lvl + 3.0
    c = _common(rng, n)
    log1p_vol_p = 7 + vol_link * (ldv - ldv.mean()) + rng.normal(0, 1, n)
    log_rv = -5 + rv_link * (ldv - ldv.mean()) + rng.normal(0, 0.5, n)
    if liq_link:
        c["liq"] = np.exp(11 + 1.5 * (ldv - ldv.mean()))
    dV = np.expm1(ldv)
    u = pd.DataFrame({"market_id": [f"m{m}" for m in mk], "event_id": [f"e{e}" for e in ev], "skey": [f"s{m % 20}" for m in mk], "day": "2026-10-20", "slot": j, "t_row": j * 7200.0,
                      "x": rng.uniform(-0.004, 0.004, n), "spread": rng.uniform(0.01, 0.05, n), "ltp": 0.5, "ltp_present": 1.0, "bid": 0.49, "ask": 0.51, "vol24": np.exp(log1p_vol_p),
                      "vol24_p": np.exp(log1p_vol_p), "dV": dV, "rv24s": np.exp(log_rv), "rv_floor": 0.0, "d24": np.abs(rng.normal(0, 0.02, n)), "d24_flag": 0.0,
                      "dV_lag": np.expm1(np.maximum(ldv_lag, 0.1)), "lag_rolloff": 0.0, **c})
    u["ldv"], u["ldv_lag"] = np.log1p(u["dV"]), np.log1p(np.maximum(u["dV_lag"], 0.0))
    u["log_rv24s"] = np.log(u["rv24s"])
    u["log1p_vol_p"] = np.log1p(u["vol24_p"])
    if one_per_market:
        u["market_id"] = [f"m{i}" for i in range(n)]
    tot = {"eligible": 3000, "volume_present": 900, "rolloff_negative_dv": 100}
    return _finish(u), tot


@pytest.mark.parametrize("mut,fails", [
    ({}, None), ({"narrow": True}, "resid_iqr"), ({"vol_link": 1.5}, "corr_log1p_vol_p"), ({"rv_link": 1.5}, "corr_log_rv24s"), ({"liq_link": True}, "corr_liq"),
    ({"one_per_market": True}, "block_share"), ({"lag_rho": 0.95}, "corr_lag")])
def test_ch193_gates(mut, fails):
    U, tot = pop193(**mut)
    r = lt.census_ch193(U, tot, SPEC, SCALE, COV + 5)
    g = r["gate_CH193"]
    if fails is None:
        assert g["pass"] is True, g
        assert r["slope"]["mde_tercile_c"] <= 0.5 and r["F"]["f_mde_c"] <= 0.5 and r["block_min_units"] == 6 and r["requires"].startswith("CV7")
    else:
        assert g[fails] is False and g["pass"] is False, g


def test_ch193_volume_share_units_and_lag_arm():
    U, tot = pop193()
    low = lt.census_ch193(U, {"eligible": 10_000, "volume_present": 900, "rolloff_negative_dv": 1}, SPEC, SCALE, 7.0)["gate_CH193"]
    assert low["volume_present"] is False  # 9% < 15%
    assert lt.census_ch193(U, tot, SPEC, 1.0, 7.0)["gate_CH193"]["units"] is False  # 8,000 < 100,800
    # the lag arm uses the units that HAVE the lag; missing lags are NaN and drop out of the arm, never 0
    U2 = U.copy()
    U2.loc[U2.index[: len(U2) // 2], ["dV_lag", "ldv_lag"]] = np.nan
    r = lt.census_ch193(U2, tot, SPEC, SCALE, 7.0)
    assert r["arm_units"] == len(U2) // 2 and r["arm_share"] == pytest.approx(0.5) and r["dV_lag_missing_share"] == pytest.approx(0.5)
    assert r["F"]["f_mde_c"] == max(r["F"]["declared_c"], r["F"]["design_c"])
    # a negative lag change is observed: clamped with the lag_rolloff indicator in the arm model, counted
    U3 = U.copy()
    U3.loc[U3.index[:100], "dV_lag"] = -50.0
    U3["ldv_lag"] = np.log1p(np.maximum(U3["dV_lag"], 0.0))
    U3["lag_rolloff"] = (U3["dV_lag"] < 0).astype(float)
    r3 = lt.census_ch193(U3, tot, SPEC, SCALE, 7.0)
    assert r3["dV_lag_negative_share"] == pytest.approx(100 / len(U3)) and np.isfinite(r3["F"]["design_c"])


# --- CH192 -----------------------------------------------------------------------------------------------------------------------------


def pop192(*, n_m=200, per=40, lag_rho=0.0, rv_link=0.0, liq_link=False, narrow=False, floor_share=0.1, one_per_market=False, seed=0):
    rng = np.random.default_rng(seed)
    n = n_m * per
    mk, ev = _ids(n, n_m)
    j = np.tile(np.arange(per), n_m)
    e1, e2 = rng.normal(size=n), rng.normal(size=n)
    lvl = np.repeat(rng.normal(size=n_m), per)
    log_rv = -5 + rng.normal(0, 0.5, n)
    ivr = 1.0 + (0.0 if narrow else 1.0) * (lvl + e1) + rv_link * (log_rv + 5) + (0.01 * e1 if narrow else 0.0)
    ivr_lag = lag_rho * e1 + math.sqrt(1 - lag_rho**2) * e2 + lvl + 1.0
    c = _common(rng, n)
    if liq_link:
        c["liq"] = np.exp(11 + 1.5 * (ivr - ivr.mean()))
    u = pd.DataFrame({"market_id": [f"m{m}" for m in mk], "event_id": [f"e{e}" for e in ev], "skey": [f"s{m % 20}" for m in mk], "day": "2026-10-20", "slot": j, "t_row": j * 7200.0,
                      "spread": rng.uniform(0.01, 0.05, n), "vol24": np.exp(rng.normal(7, 1, n)), "rv24": np.exp(log_rv), "rv24s": np.exp(log_rv), "rv_floor": (rng.random(n) < floor_share).astype(float),
                      "rv7d": np.exp(rng.normal(-5, 0.3, n)), "ivr": ivr, "ivr_lag": ivr_lag, "rewarded": rng.integers(0, 2, n).astype(float), "in_band": rng.integers(0, 2, n).astype(float),
                      "anat": rng.choice(["traded", "quote_only", "non_mover"], n), **c})
    u["log_rv24s"], u["log_rv7d"] = np.log(u["rv24s"]), np.log(u["rv7d"])
    u["log1p_vol"] = np.log1p(u["vol24"])
    u["spread_eq_tick"] = (rng.random(n) < 0.2).astype(float)
    u["spread_g"] = u["spread"]
    u["ivr_g"] = u["ivr"]
    u["rv7d_floor"] = 0.0
    for nm in ("traded", "quote_only", "ambiguous", "never_traded"):
        u[f"an_{nm}"] = (u["anat"] == nm).astype(float)
    if one_per_market:
        u["market_id"] = [f"m{i}" for i in range(n)]
    return _finish(u), {"eligible": n}


@pytest.mark.parametrize("mut,fails", [
    ({}, None), ({"floor_share": 0.7}, "rv_floor_share"), ({"narrow": True}, "resid_iqr"), ({"rv_link": 2.5}, "corr_zivr_log_rv24"), ({"liq_link": True}, "corr_liq"),
    ({"one_per_market": True}, "block_share"), ({"lag_rho": 0.95}, "corr_lag")])
def test_ch192_gates(mut, fails):
    U, tot = pop192(**mut)
    r = lt.census_ch192(U, tot, SPEC, SCALE, 2.75)
    g = r["gate_CH192"]
    if fails is None:
        assert g["pass"] is True, g
        assert r["slope"]["mde_tercile_c"] <= 0.5 and r["F"]["f_mde_c"] <= 0.5 and r["block_min_units"] == 3
    else:
        assert g[fails] is False and g["pass"] is False, g


def test_ch192_units_and_minimum_days():
    U, tot = pop192()
    assert lt.census_ch192(U, tot, SPEC, 1.0, 2.75)["gate_CH192"]["units"] is False  # 8,000 < 210,000
    assert lt.census_ch192(U, tot, SPEC, SCALE, 1.9)["gate_CH192"]["pass"] is False  # minimum 2 covered days (four slots a day)
    assert lt.census_ch192(U, tot, SPEC, SCALE, 2.0)["gate_CH192"]["covered_days"] is True


def test_spec_gate_thresholds_are_the_declared_ones():
    g = SPEC["census_gates"]
    assert g["CS7_CH195"]["units_projected_min"] == 42000 and g["CC7_CH191"]["units_projected_min"] == 201600 and g["CS7_CH197"]["units_projected_min"] == 210000
    assert g["CC7_CH193"]["units_projected_min"] == 100800 and g["CC7_CH192"]["units_projected_min"] == 210000
    assert g["CC7_CH191"]["class_share_min"] == 0.15 and g["CS7_CH195"]["coverage_min"] == 0.70 and g["CS7_CH195"]["sign_agree_min"] == 0.70
    assert g["CS7_CH197"]["covered_share_min"] == 0.60 and g["CS7_CH197"]["r_gate_max"] == 0.8 and g["CS7_CH197"]["day_diff_min"] == 0.1
    assert g["CC7_CH193"]["volume_present_share_min"] == 0.15 and g["CC7_CH193"]["resid_iqr_min"] == 0.5 and g["CC7_CH193"]["lag_corr_max"] == 0.8
    assert g["CC7_CH192"]["rv_floor_share_max"] == 0.5 and g["CC7_CH192"]["resid_iqr_min"] == 0.15 and g["CC7_CH192"]["corr_zivr_logrv_max"] == 0.7 and g["CC7_CH192"]["resid_iqr_min_units"] == 8
    assert g["CS7_CH195"]["resid_iqr_min"] == 0.25 and g["CS7_CH195"]["corr_zR_zRaway_max"] == 0.8
    assert g["CV7_CH193"]["traded_share_min"] == 0.70 and g["CV7_CH193"]["untraded_share_max"] == 0.30 and g["CV7_CH193"]["spearman_min"] == 0.5
    assert g["CV7_CH193"]["latency_window_s"] == 1800 and g["CV7_CH193"]["latency_min_intervals"] == 30 and g["CV7_CH193"]["min_sample_notional"] == 10.0
    a = g["mde_common"]
    assert (a["t_sum"], a["day_factor"], a["mde_max"], a["f_mde_max"], a["planning_de"]) == (3.47, 1.5, 0.005, 0.005, 6.196)
    assert (g["CS7_CH195"]["de_floor"], g["CC7_CH191"]["de_floor"], g["CC7_CH193"]["de_floor"], g["CS7_CH197"]["de_floor"], g["CC7_CH192"]["de_floor"]) == (3.0, 3.0, 3.0, 5.0, 5.0)
    assert (a["sd_c_skip"], a["sd_y22"], a["sd_a"], a["sd_a_s"]) == (0.05, 0.06, 0.03, 0.03)
    assert SPEC["census_inputs"]["min_covered_days"] == {"CC7": 5, "CC7_CH192": 2, "CS7_CH195": 1.5, "CS7_CH197": 2, "CV7": 1.5}
    assert copy.deepcopy(SPEC)["census_inputs"]["refuse_at_or_after_utc"] == "2026-10-22T00:00:00Z"


# --- census-code check fixes ---------------------------------------------------------------------------------------------------------


def test_multiplier_is_the_larger_of_declared_and_exact():
    a = lt.mde_common(SPEC)
    assert SPEC["census_gates"]["mde_common"]["t_sum"] == 3.47  # the declared value is untouched in the spec
    assert a["t_sum"] == max(3.47, lt.exact_t_sum()) and a["t_sum"] > 3.47 and abs(a["t_sum"] - 3.4725) < 5e-4
    assert a["t_sum_declared"] == 3.47
    U, tot = pop195()
    assert lt.census_ch195(U, tot, SPEC, SCALE, COV)["t_sum_used"] == a["t_sum"]
    low = copy.deepcopy(SPEC)
    low["census_gates"]["mde_common"]["t_sum"] = 5.0  # a larger declared value is never lowered
    assert lt.mde_common(low)["t_sum"] == 5.0


def test_in_band_is_nan_when_the_reward_spread_is_missing_inside_the_band():
    band = SPEC["tests"]["CH197"]["reward_band"]
    r = lt._in_band([0.5, 0.5, 0.5, 0.95, 0.5], [0.02, 0.05, 0.02, 0.02, 0.02], [3.5, 3.5, np.nan, np.nan, 0.0], band)
    assert r[0] == 1.0 and r[1] == 0.0  # 5c > 3.5c
    assert np.isnan(r[2])  # mid in band and rewards_max_spread missing: NaN (excluded, counted), never 0
    assert r[3] == 0.0  # mid outside the band: 0 whatever the field
    assert r[4] == 0.0  # a zero maximum spread: out of band


def test_ch192_lag_gate_uses_the_larger_abs_correlation_of_the_two_origin_definitions():
    U, tot = pop192()
    r0 = lt.census_ch192(U, tot, SPEC, SCALE, 2.75)
    assert r0["origin_spread_definitions_agree_share"] == 1.0 and r0["gate_CH192"]["corr_lag"] is True and "rv7d_floor_share" in r0
    U2 = U.copy()
    U2["ivr_g"] = U2["ivr_lag"] * 0.97 + np.random.default_rng(3).normal(0, 0.1, len(U2))  # Gamma's origin spread tracks the lag: r large
    U2["spread_g"] = U2["spread"] * 1.5
    r = lt.census_ch192(U2, tot, SPEC, SCALE, 2.75)
    assert abs(r["r_w_used"]) > 0.8 and abs(r["r_w_used"]) >= abs(r["corr_lag"]["within"]) and r["gate_CH192"]["corr_lag"] is False
    assert r["origin_spread_definitions_agree_share"] == 0.0


def test_events_two_day_formula_and_descriptives_present():
    pop = pd.DataFrame({"event_id": ["a", "b", "b", "c", "d", "e"], "day": ["d1", "d1", "d1", "d2", "d2", "d2"]})
    e = lt._events(pop, 10.5, 2.0)
    assert e["events"] == 5 and e["events_day1"] == 2 and e["events_projected_21d"] == 5 + (5 - 2) * 19 and e["rule"].startswith("E_2d")
    pop3 = pd.DataFrame({"event_id": list("abc"), "day": ["d1", "d2", "d3"]})
    assert lt._events(pop3, 3.0, 7.0)["events_projected_21d"] == 9.0
    U, tot = pop195()
    r = lt.census_ch195(U, tot, SPEC, SCALE, COV)
    assert {"corr_v_prev_printed", "liquidity_tiers_top_zR_share", "projected_units_21d_after_family_exclusion", "events"} <= set(r)
    assert set(r["liquidity_tiers_top_zR_share"]) == {"low", "mid", "high"}
    U7, t7 = pop197()
    r7 = lt.census_ch197(U7, t7, SPEC, SCALE, COV, pairs197())
    assert {"corr_imbT_1c_form_printed", "rewarded_share_by_zimbB_tercile", "liquidity_tiers_top_zimbB_share"} <= set(r7) and r7["events"]["rule"].startswith("E_2d")
    ov = lt.unit_overlaps({"A": pd.DataFrame({"market_id": ["m1", "m2", "m3"], "slot": [1, 1, 2]}), "B": pd.DataFrame({"market_id": ["m1", "m3"], "slot": [1, 3]})})
    assert ov["A&B"]["units"] == 1 and ov["A&B"]["share_of_A"] == pytest.approx(1 / 3)
    uf = pop195(per=40)[0]
    uf["skey"] = np.where(np.arange(len(uf)) % 10 < 5, "big", uf["skey"])
    rf = lt.census_ch195(uf, tot, SPEC, SCALE, COV)
    assert rf["projected_units_21d_after_family_exclusion"] < rf["projected_units_21d"]
