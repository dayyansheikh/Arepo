# ruff: noqa: E501
"""LT7 (LIVE_TESTS_7.md) code phase 1: the pure rules of the unit builders and the census statistics, on synthetic frames. Synthetic
data only; no network; no real data, outcome or target field is read."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import live_tests7 as lt
from astrolabe.research_lab import live_tests7_base as b

SPEC = lt.load_spec(sha=None)
T0 = lt.epoch("2026-10-09T12:31:05Z")  # a 12:31Z capture (slot 6 of its UTC day)
K0 = b.slot_of(lt.epoch("2026-10-09T12:31:00Z"), SPEC)
assert lt.slot_in_day(K0) == 6
CAP = {"id": "c", "start": T0, "dir": "."}


def ser_frame(mids: dict, *, t: float = T0, spread: float = 0.02, sports: int = 0, crypto7: str = "non_crypto", vol: float | dict = 1000.0, ltp: float | dict = 0.5,
              tick: float = 0.01, liq: float = 1e5, event: str = "e1", end_h: float = 500.0, rew: float = 10.0, bid_ask: dict | None = None) -> pd.DataFrame:
    """A series frame (index market_id) as :func:`live_tests7.series7_frame` writes it."""
    ids = list(mids)
    mid = np.array([mids[m] for m in ids], float)
    bid = np.array([bid_ask[m][0] if bid_ask and m in bid_ask else mid[i] - spread / 2 for i, m in enumerate(ids)])
    ask = np.array([bid_ask[m][1] if bid_ask and m in bid_ask else mid[i] + spread / 2 for i, m in enumerate(ids)])
    f = lambda v: np.array([v[m] if isinstance(v, dict) else v for m in ids], float)  # noqa: E731
    return pd.DataFrame({
        "event_id": [event if not isinstance(event, dict) else event[m] for m in ids], "t_row": t, "bid": bid, "ask": ask, "spread": ask - bid, "ltp": f(ltp), "vol24": f(vol),
        "end_ts": t + end_h * 3600.0, "created_ts": np.nan, "chg_1h": 0.0, "chg_1d": 0.0, "chg_1w": 0.0, "neg_risk": 0,
        "sports": sports if not isinstance(sports, dict) else [sports[m] for m in ids], "crypto": 0, "skey": [f"event:{m}" for m in ids], "tick": tick,
        "fee_rate": 0.0, "fee_exp": 1.0, "liq": liq, "rew_rate": rew, "rew_min": 20.0, "rew_maxspread": 3.5, "osz": 5.0, "fee_cat": "Politics",
        "crypto7": crypto7 if not isinstance(crypto7, dict) else [crypto7[m] for m in ids]}, index=pd.Index(ids, name="market_id"))


def store_with(paths: dict[str, list[float]], k: int, *, tick_spread: float = 0.02, missing: dict | None = None) -> lt.MidStore:
    """MidStore with slots k - len + 1 .. k; ``paths[m]`` lists the mids oldest first; ``missing`` {market: set of slot offsets from k (negative)} absent."""
    n = len(next(iter(paths.values())))
    st = lt.MidStore()
    for i in range(n):
        slot = k - (n - 1) + i
        mids = {m: p[i] for m, p in paths.items() if not (missing and i - (n - 1) in missing.get(m, set()))}
        if mids:
            st.add(slot, ser_frame(mids, spread=tick_spread))
    return st


# --- crypto classifier ---------------------------------------------------------------------------------------------------------


def test_crypto_classifier_and_failsafe():
    assert lt.crypto_class("Crypto") == "crypto" and lt.crypto_class("  CRYPTO_fees ") == "crypto" and lt.crypto_class("Politics") == "non_crypto"
    for v in (None, float("nan"), "", "  ", "None", "null", "NaN"):
        assert lt.crypto_class(v) == "unknown"
    assert lt.crypto_class("Crypto", sidecar_present=False) == "unknown" and lt.crypto_class("Politics", sports=-1) == "unknown"
    assert lt.crypto_failsafe({"Politics": 5, "Crypto": 1})["classifier_shown_to_work"] is True
    fs = lt.crypto_failsafe({"Politics": 5, "Sports": 2})
    assert fs["classifier_shown_to_work"] is False and math.isnan(fs["gate_value"])


def test_category_rule_excludes_sports_crypto_and_unknown():
    s = ser_frame({"a": 0.5, "b": 0.5, "c": 0.5, "d": 0.5, "e": 0.5}, sports={"a": 0, "b": 1, "c": 0, "d": -1, "e": 0},
                  crypto7={"a": "non_crypto", "b": "non_crypto", "c": "crypto", "d": "unknown", "e": "unknown"})
    s["x"] = 0.0
    cnt: dict = {}
    out = lt._non_sports_ex_crypto(s.reset_index(), cnt)
    assert list(out["market_id"]) == ["a"] and cnt == {"sports_unknown": 1, "sports": 1, "crypto": 1, "crypto_unknown": 1}


# --- scaled block-gate share proxy (R1 re-check must-fix 1) ---------------------------------------------------------------------------


def test_block_min_units_scaling():
    assert lt.block_min_units(2) == 2 and lt.block_min_units(7) == 6 and lt.block_min_units(6.83) == 6 and lt.block_min_units(2.75) == 3
    assert lt.block_min_units(21) == 16 and lt.block_min_units(1.5) == 2 and lt.block_min_units(0.5) == 1
    assert lt.block_min_units(float("nan")) == float("inf") and lt.block_min_units(0) == float("inf")


def test_block_share_uses_the_proxy():
    pop = pd.DataFrame({"market_id": ["a"] * 6 + ["b"] * 5 + ["c"] * 1})
    assert lt.block_share(pop, 6) == pytest.approx(6 / 12)
    assert lt.block_share(pop, 2) == pytest.approx(11 / 12)
    assert math.isnan(lt.block_share(pop.iloc[0:0], 2)) and math.isnan(lt.block_share(pop, float("inf")))


# --- rv and the mid store (look-back from the reader's own earlier series) ---------------------------------------------------------------


def test_rv24_ten_of_twelve_and_rv7d_sixty_of_eighty_four():
    k = K0
    flat = {"flat": [0.5] * 85, "walk": [0.5 + 0.01 * (i % 2) for i in range(85)]}
    st = store_with(flat, k)
    M = st.matrix(k, 12, ["flat", "walk", "nope"], "mid")
    rv, n = lt.rv_from_matrix(M, 10)
    assert n[0] == 12 and rv[0] == 0.0 and n[1] == 12 and rv[1] == pytest.approx(0.01) and np.isnan(rv[2])
    # 3 of 13 mids missing
    st2 = store_with(flat, k, missing={"walk": {-1, -5, -9}})
    rv2, n2 = lt.rv_from_matrix(st2.matrix(k, 12, ["walk"], "mid"), 10)
    assert n2[0] == 6 and np.isnan(rv2[0])  # three non-adjacent absent mids cut six of the 12 changes
    st3 = store_with(flat, k, missing={"walk": {-2}})
    rv3, n3 = lt.rv_from_matrix(st3.matrix(k, 12, ["walk"], "mid"), 10)
    assert n3[0] == 10 and rv3[0] == pytest.approx(0.01)
    # 84 changes: 60 observed passes, 59 do not
    miss60 = {-i for i in range(1, 85) if i % 2 == 0 and i <= 50}  # 25 absent mids, none adjacent
    st4 = store_with({"w": [0.5 + 0.01 * (i % 2) for i in range(85)]}, k, missing={"w": miss60})
    _, n4 = lt.rv_from_matrix(st4.matrix(k, 84, ["w"], "mid"), 60)
    assert n4[0] == 84 - 50
    rv5, _ = lt.rv_from_matrix(st4.matrix(k, 84, ["w"], "mid"), 34)
    assert np.isfinite(rv5[0])
    rvs, flag = lt.floored_rv(np.array([0.0, 0.004, 0.02, np.nan]), np.array([0.01, 0.01, 0.01, 0.01]), 0.5)
    assert list(rvs[:3]) == [0.005, 0.005, 0.02] and list(flag[:3]) == [1.0, 1.0, 0.0] and np.isnan(rvs[3]) and np.isnan(flag[3])


# --- CH195 -----------------------------------------------------------------------------------------------------------------------------


def sweep_frame(rows: dict, t: float) -> pd.DataFrame:
    """rows: market -> (bid, ask, dbid5, dask5[, two])."""
    d = {m: {"sbid": v[0], "sask": v[1], "s_t": t + 400.0, "s_two": 1 if len(v) < 5 else v[4], "bsz1": 50.0, "asz1": 40.0, "dbid1": 60.0, "dask1": 50.0, "dbid5": v[2], "dask5": v[3]} for m, v in rows.items()}
    return pd.DataFrame(d).T.rename_axis("market_id")


def test_resist_hit_and_away_sides_for_rises_and_falls():
    mk = ["up", "dn", "bad_sign", "gap", "sports"]
    p = {"up": 0.50, "dn": 0.50, "bad_sign": 0.50, "gap": 0.50, "sports": 0.50}
    k = {"up": 0.53, "dn": 0.47, "bad_sign": 0.53, "gap": 0.53, "sports": 0.53}
    ser_p = ser_frame(p, t=T0 - 7200, vol=1000.0, ltp=0.5)
    ser_k = ser_frame(k, t=T0, vol=dict.fromkeys(mk, 1100.0), ltp=k, sports={"up": 0, "dn": 0, "bad_sign": 0, "gap": 0, "sports": 1})
    # sweep k - 1: outcome-0 books; (bid, ask, dbid5, dask5)
    sw_p = sweep_frame({"up": (0.49, 0.51, 300.0, 900.0), "dn": (0.49, 0.51, 800.0, 200.0), "bad_sign": (0.49, 0.51, 300.0, 900.0), "gap": (0.49, 0.51, np.nan, 900.0),
                        "sports": (0.49, 0.51, 300.0, 900.0)}, T0 - 7200)
    sw_k = sweep_frame({"up": (0.52, 0.54, 300.0, 900.0), "dn": (0.46, 0.48, 800.0, 200.0), "bad_sign": (0.48, 0.50, 300.0, 900.0), "gap": (0.52, 0.54, 300.0, 900.0),
                        "sports": (0.52, 0.54, 300.0, 900.0)}, T0)
    st = None
    u, cnt = lt.resist_units(ser_k, ser_p, st, sw_k, sw_p, CAP, K0, SPEC)
    assert set(u["market_id"]) == {"up", "dn"} and cnt["sign_disagree"] == 1 and cnt["sports"] == 1 and cnt["covered"] == 3  # 'gap' lacks a depth
    up, dn = u.set_index("market_id").loc["up"], u.set_index("market_id").loc["dn"]
    # a rise hits the asks: D_hit = ask 5c depth x ask touch of the PRE-move sweep; away = bid side
    assert up["D_hit"] == pytest.approx(900.0 * 0.51) and up["D_away"] == pytest.approx(300.0 * 0.49)
    # a fall hits the bids
    assert dn["D_hit"] == pytest.approx(800.0 * 0.49) and dn["D_away"] == pytest.approx(200.0 * 0.51)
    assert up["R"] == pytest.approx(math.log1p(900.0 * 0.51)) and up["R_away"] == pytest.approx(math.log1p(300.0 * 0.49))
    # decision time is sweep 1 of pass k
    assert up["t_row"] == T0 + 400.0
    # h0 from the pass-k book on outcome 0
    liq = 1e5
    assert up["h0"] == pytest.approx(np.clip(1 - (300.0 * 0.52 + 900.0 * 0.54) / liq, 0, 1))
    u2, c2 = lt.resist_units(ser_k, ser_p, st, None, sw_p, CAP, K0, SPEC)
    assert u2.empty and c2["nosweep"] == 1
    u3, c3 = lt.resist_units(ser_k, ser_p, st, sw_k, None, CAP, K0, SPEC)
    assert u3.empty and c3["noprevsweep"] == 1


def test_resist_requires_band_movers_and_wide_sweeps_excluded():
    ser_p = ser_frame({"hi": 0.94, "lowq": 0.50}, t=T0 - 7200)
    ser_k = ser_frame({"hi": 0.96, "lowq": 0.505}, t=T0, ltp=0.5)  # 'hi' outside [0.07, 0.93]; 'lowq' moves 0.5c (< 1c)
    sw = sweep_frame({"hi": (0.9, 0.97, 300.0, 300.0), "lowq": (0.5, 0.51, 300.0, 300.0)}, T0)
    u, cnt = lt.resist_units(ser_k, ser_p, None, sw, sw, CAP, K0, SPEC)
    assert u.empty and cnt["movers"] == 0


# --- CH191 -----------------------------------------------------------------------------------------------------------------------------


def path_world(steps_by_market: dict[str, tuple[float, float, float]], *, k: int = K0, start: float = 0.40, absent_slot: dict | None = None):
    """Mid paths for slots k - 12 .. k: flat at ``start`` until k - 3, then the three steps s3, s2, s1 (oldest first)."""
    paths = {}
    for m, (s3, s2, s1) in steps_by_market.items():
        p = [start] * 10 + [start + s3, start + s3 + s2, start + s3 + s2 + s1]
        paths[m] = p
    return paths


def run_path(steps, **kw):
    paths = path_world(steps)
    st = store_with(paths, K0, missing=kw.pop("missing", None))
    mids_k = {m: p[-1] for m, p in paths.items()}
    mids_p = {m: p[-2] for m, p in paths.items()}
    ser_k = ser_frame(mids_k, t=T0, vol=1100.0, ltp=0.5, **kw)
    ser_p = ser_frame(mids_p, t=T0 - 7200, vol=1000.0, ltp=0.5)
    return lt.path_units7(ser_k, ser_p, st, CAP, K0, SPEC)


def test_ch191_grind_jump_and_the_every_step_rule():
    steps = {"grind": (0.01, 0.01, 0.01), "grind3": (0.02, 0.02, 0.02), "jump": (0.0, 0.0, 0.05), "jump_first": (0.05, 0.0, 0.0),
             "two_two_zero": (0.02, 0.02, 0.0), "short": (0.01, 0.01, 0.0), "zig": (0.03, -0.02, 0.03), "small_move": (0.0, 0.01, 0.01)}
    u, cnt = run_path(steps)
    c = u.set_index("market_id")["cls6"]
    assert c["grind"] == "grind" and c["grind3"] == "grind" and c["jump"] == "jump" and c["jump_first"] == "jump"
    # (2c, 2c, 0) is NOT a grind (R1 must-fix 11): its last step is not three same-signed steps
    assert c["two_two_zero"] != "grind" and c["two_two_zero"] == "other"
    assert "short" not in c.index and "small_move" not in c.index  # |x6| < 3 ticks / < 2c
    assert cnt["x6_below_threshold_or_tick_unknown"] >= 2 and cnt["every_step_rule_loss"] >= 1
    g = u.set_index("market_id")
    assert g.loc["grind", "G"] == 1.0 and g.loc["jump", "G"] == 0.0
    assert g.loc["jump", "pc"] == 1.0 and g.loc["grind", "pc"] == pytest.approx(1 / 3) and g.loc["grind", "sa"] == pytest.approx(1.0)
    assert g.loc["jump_first", "last_cls"] == "small_last_step"  # a jump in the first step leaves a flat last step


def test_ch191_three_tick_rule_and_missing_step_slot():
    # |x6| = 0.03 with a 0.02 tick fails the 3-tick rule; with a 0.01 tick it passes
    u, cnt = run_path({"a": (0.01, 0.01, 0.01)}, tick=0.02)
    assert u.empty and cnt["x6_below_threshold_or_tick_unknown"] == 1
    u, _ = run_path({"a": (0.01, 0.01, 0.01)}, tick=0.01)
    assert len(u) == 1
    # a missing step slot (k - 2 absent for the market) gives no unit
    u, cnt = run_path({"a": (0.01, 0.01, 0.01), "b": (0.01, 0.01, 0.01)}, missing={"a": {-2}})
    assert list(u["market_id"]) == ["b"] and cnt["step_slot_missing"] == 1


def test_ch191_rv24_defined_and_floored():
    u, _ = run_path({"a": (0.01, 0.01, 0.01)})
    r = u.iloc[0]
    assert r["rv24s"] >= 0.005 and r["rv_floor"] in (0.0, 1.0) and r["log_rv24s"] == pytest.approx(math.log(r["rv24s"]))
    # fewer than 10 of 12 changes observed: no unit
    u, cnt = run_path({"a": (0.01, 0.01, 0.01)}, missing={"a": {-12, -11, -10, -8, -7}})
    assert u.empty and cnt["rv24_undefined"] == 1


# --- CH197 -----------------------------------------------------------------------------------------------------------------------------


def test_behind_touch_imbalances():
    r = lt.behind_touch([50.0, 10.0, 30.0, np.nan], [40.0, 10.0, 20.0, 5.0], [150.0, 10.0, 20.0, 50.0], [120.0, 10.0, 90.0, 60.0])
    # bT, aT = 50, 40; bB, aB = 100, 80 -> imbT = 10/90, imbB = 20/180
    assert r["imbT"][0] == pytest.approx(10 / 90) and r["imbB"][0] == pytest.approx(20 / 180)
    assert np.isnan(r["imbB"][1]) and r["behind_zero"][1]  # bB + aB = 0 excluded, counted
    assert np.isnan(r["imbB"][2]) and r["behind_negative"][2]  # inconsistent book, counted apart
    assert np.isnan(r["imbT"][3]) and np.isnan(r["imbB"][3])


def sweep_frame_sizes(rows: dict, t: float) -> pd.DataFrame:
    d = {m: {"sbid": v[0], "sask": v[1], "s_t": t + 400.0, "s_two": 1, "bsz1": v[2], "asz1": v[3], "dbid1": 1.0, "dask1": 1.0, "dbid5": v[4], "dask5": v[5]} for m, v in rows.items()}
    return pd.DataFrame(d).T.rename_axis("market_id")


def test_patient_units_slot_filters_and_states():
    k = K0
    ser_p = ser_frame({"a": 0.50, "b": 0.50, "c": 0.50, "d": 0.50, "e": 0.5}, t=T0 - 7200)
    ser_k = ser_frame({"a": 0.50, "b": 0.50, "c": 0.50, "d": 0.50, "e": 0.5}, t=T0, end_h=20.0)  # end within 27 h: no unit at all
    sw = sweep_frame_sizes({"a": (0.49, 0.51, 50, 40, 150, 120), "b": (0.49, 0.51, 10, 10, 10, 10), "c": (0.49, 0.58, 50, 40, 150, 120),
                            "d": (0.49, 0.51, 50, 40, 150, 120), "e": (0.49, 0.51, 50, 40, 150, 120)}, T0)
    u, cnt = lt.patient_units(ser_k, ser_p, None, sw, CAP, k, SPEC)
    assert u.empty and cnt["end_date"] == 5
    ser_k = ser_frame({"a": 0.50, "b": 0.50, "c": 0.50, "d": 0.50, "e": 0.5}, t=T0, end_h=500.0)
    u, cnt = lt.patient_units(ser_k, ser_p, None, sw, CAP, k, SPEC)
    assert set(u["market_id"]) == {"a", "d", "e"}  # b: bB + aB = 0; c: sweep spread 0.09 > 0.05
    assert cnt["behind_zero_excluded"] == 1 and cnt["sweep_not_tight"] == 1 and cnt["books_in_band"] == 5
    a = u.set_index("market_id").loc["a"]
    assert a["imbT"] == pytest.approx(10 / 90) and a["imbB"] == pytest.approx(20 / 180) and a["t_row"] == T0 + 400.0 and a["dis"] == pytest.approx(a["imbB"] - a["imbT"])
    assert a["rewarded"] == 1.0 and a["in_band"] == 1.0 and a["day"] == "2026-10-09"
    # only the 12:31Z pass gives units; the pair loader lifts that restriction
    u6, c6 = lt.patient_units(ser_k, ser_p, None, sw, CAP, k + 1, SPEC)
    assert u6.empty and c6["not_1231_pass"] == 1
    u7, _ = lt.patient_units(ser_k, ser_p, None, sw, CAP, k + 1, SPEC, any_slot=True)
    assert len(u7) == 3


def test_pair_correlations_with_one_1231_pair_per_market():
    """R1 must-fix 1: pairs from ANY slot; the first pair of a market drops by demeaning; markets with < 3 pairs are excluded; a synthetic seal with one
    12:31Z pair per market still gives a finite r_w from the other pairs; r_gate = max(r_w, r_pool)."""
    rng = np.random.default_rng(1)
    rows = []
    for m in range(40):
        lvl = rng.normal()
        for j in range(8):
            a = lvl * 0.5 + rng.normal() * 0.3
            rows.append({"market_id": f"m{m}", "t_row": float(j * 7200), "imb_j": a, "imb_j13": 0.8 * a + 0.2 * rng.normal()})
    pairs = pd.DataFrame(rows)
    r = lt.pair_correlations(pairs, 3)
    assert np.isfinite(r["r_w"]) and np.isfinite(r["r_pool"]) and r["r_gate"] == max(r["r_w"], r["r_pool"]) and r["markets"] == 40
    assert r["r_pool"] > r["r_w"]  # the pooled correlation carries the market level
    # markets with fewer than 3 pairs are excluded
    few = pairs[pairs["market_id"].isin([f"m{m}" for m in range(5)]) & (pairs["t_row"] < 2 * 7200)]
    assert lt.pair_correlations(few, 3)["markets"] == 0 and math.isnan(lt.pair_correlations(few, 3)["r_gate"])
    only_one = pairs.groupby("market_id").head(1)
    assert math.isnan(lt.pair_correlations(only_one, 3)["r_w"])
    assert math.isnan(lt.pair_correlations(pairs.iloc[0:0], 3)["r_gate"])


# --- CH193 -----------------------------------------------------------------------------------------------------------------------------


def test_absorbed_units_rules_and_lag():
    k = K0
    mids = {m: 0.5 for m in "abcdefg"}
    mids_k = dict(mids, f=0.502, g=0.51)
    ser_p = ser_frame(mids, t=T0 - 7200, vol=dict(zip("abcdefg", [1000.0] * 7, strict=True)))
    vol_k = {"a": 1100.0, "b": 1000.0, "c": 900.0, "d": 1005.0, "e": np.nan, "f": 1300.0, "g": 1300.0}
    ser_k = ser_frame(mids_k, t=T0, vol=vol_k)
    st = store_with({m: [0.5] * 13 for m in mids}, k)
    v2 = pd.Series({"a": 5000.0, "b": 5000.0, "c": 5000.0, "d": 5000.0, "f": 5000.0, "g": 5000.0})
    v3 = pd.Series({"a": 5200.0, "b": 4000.0, "c": 5300.0, "d": 5100.0, "f": np.nan, "g": 5600.0})
    u, cnt = lt.absorbed_units(ser_k, ser_p, st, CAP, k, SPEC, v2, v3)
    ids = set(u["market_id"])
    # a: dV 100 > max(10, 0.1) ok; b: dV 0; c: negative dV (roll-off) is no unit; d: dV 5 below the $10 floor; e: volume missing; f: |x| 0.2c ok; g: moved 1c, no unit
    assert ids == {"a", "f"} and cnt["rolloff_negative_dv"] == 1 and cnt["moved"] == 1 and cnt["volume_present"] == 6
    r = u.set_index("market_id")
    assert r.loc["a", "dV"] == 100.0 and r.loc["a", "ldv"] == pytest.approx(math.log1p(100.0))
    # the target is NOT in the unit: only origin-side columns (no mid at k + 1 / k + 2)
    assert not any(c.startswith("mid_k") or c in ("a_target", "y") for c in u.columns)
    # the lag change over (k+2, k+3]; a missing lag is NaN (never 0); a negative lag is observed and clamped with lag_rolloff
    assert r.loc["a", "dV_lag"] == 200.0 and r.loc["a", "lag_rolloff"] == 0.0 and r.loc["a", "ldv_lag"] == pytest.approx(math.log1p(200.0))
    assert np.isnan(r.loc["f", "dV_lag"]) and np.isnan(r.loc["f", "ldv_lag"]) and cnt["lag_missing"] == 1
    v3b = v3.copy()
    v3b["a"] = 4000.0
    u2, cnt2 = lt.absorbed_units(ser_k, ser_p, st, CAP, k, SPEC, v2, v3b)
    a2 = u2.set_index("market_id").loc["a"]
    assert a2["dV_lag"] == -1000.0 and a2["lag_rolloff"] == 1.0 and a2["ldv_lag"] == 0.0 and cnt2["lag_rolloff"] == 1
    # no lag series at all (slots absent): every lag is missing
    u3, cnt3 = lt.absorbed_units(ser_k, ser_p, st, CAP, k, SPEC, None, None)
    assert u3["dV_lag"].isna().all() and cnt3["lag_missing"] == 2


def test_dv_tolerance_is_the_movetype_floor():
    assert list(lt.dv_tolerance([0.0, 50_000.0, 200_000.0], SPEC)) == [10.0, 10.0, 20.0]


# --- CH192 -----------------------------------------------------------------------------------------------------------------------------


def test_ivr_units_thinning_rv_definitions_and_lag():
    k = K0 - 0  # 12:31Z, a declared slot
    paths = {"a": [0.5 + 0.01 * (i % 2) for i in range(85)], "b": [0.5] * 85, "short": [0.5 + 0.01 * (i % 2) for i in range(85)]}
    missing = {"short": {-i for i in range(1, 85) if i > 20}}  # only 20 mids of the 85: rv7d undefined
    st = store_with(paths, k, missing=missing)
    ser_p = ser_frame({m: p[-2] for m, p in paths.items()}, t=T0 - 7200)
    ser_k = ser_frame({m: p[-1] for m, p in paths.items()}, t=T0, spread=0.04)
    sp3 = pd.Series({"a": 0.08, "b": 0.02, "short": 0.04})
    u, cnt = lt.ivr_units(ser_k, ser_p, st, CAP, k, SPEC, sp3)
    assert set(u["market_id"]) == {"a", "b"} and cnt["rv7d_undefined"] == 1
    r = u.set_index("market_id")
    # rv24 of a: |change| 0.01 each -> 0.01; ivr = log(spread_k / rv24*), spread_k = ask - bid; the lag spread is read over the SAME rv24*_k
    assert r.loc["a", "rv24"] == pytest.approx(0.01) and r.loc["a", "ivr"] == pytest.approx(math.log(0.04 / 0.01)) and r.loc["a", "ivr_lag"] == pytest.approx(math.log(0.08 / 0.01))
    # a flat market is floored at half a tick (rv_floor), and rv7d is floored too
    assert r.loc["b", "rv24s"] == pytest.approx(0.005) and r.loc["b", "rv_floor"] == 1.0 and np.isfinite(r.loc["b", "log_rv7d"])
    assert r.loc["b", "ivr_lag"] == pytest.approx(math.log(0.02 / 0.005))
    # slots other than 00:31 / 06:31 / 12:31 / 18:31 give no unit
    u2, c2 = lt.ivr_units(ser_k, ser_p, st, CAP, k + 1, SPEC, sp3)
    assert u2.empty and c2["not_a_declared_slot"] == 1
    assert {lt.slot_in_day(s) for s in range(K0 - 6, K0 + 12)} >= {0, 3, 6, 9}
    # a missing lag spread is NaN and never imputed
    u3, c3 = lt.ivr_units(ser_k, ser_p, st, CAP, k, SPEC, None)
    assert u3["ivr_lag"].isna().all() and c3["lag_missing"] == 2


# --- MDE and F-MDE gate formulas (max(declared, design), the 0.5c cap) ---------------------------------------------------------------


A = SPEC["census_gates"]["mde_common"]


def test_class_mde_formula():
    n1, n2, sd, de, vif = 90_000.0, 70_000.0, 0.05, 6.196, 1.3
    want = 3.47 * sd * math.sqrt(1 / n1 + 1 / n2) * math.sqrt(de) * 1.5 * math.sqrt(vif)
    assert b.mde_class(n1, n2, sd, de, A, vif) == pytest.approx(want)
    assert b.mde_class(n1, n2, sd, de, A, 0.7) == pytest.approx(3.47 * sd * math.sqrt(1 / n1 + 1 / n2) * math.sqrt(de) * 1.5)  # VIF_w floored at 1
    assert b.mde_class(0.0, n2, sd, de, A, vif) == float("inf")
    # the planning figure of the design: 0.36c at 91,200 / 76,000 (DE 6.196, VIF_w 1.3)
    assert b.mde_class(91_200, 76_000, 0.05, 6.196, A, 1.3) * 100 == pytest.approx(0.36, abs=0.005)


def test_slope_mde_takes_max_of_declared_and_design_and_nan_fails():
    rng = np.random.default_rng(3)
    n_m, per = 300, 30
    pop = pd.DataFrame({"market_id": np.repeat([f"m{i}" for i in range(n_m)], per), "t_row": np.tile(np.arange(per) * 7200.0, n_m), "event_id": np.repeat([f"e{i // 3}" for i in range(n_m)], per)})
    pop["z"] = rng.normal(size=len(pop))
    pop["c1"] = 0.5 * pop["z"] + rng.normal(size=len(pop))
    de = 6.196
    sm = lt.slope_mde(pop, "z", ["c1"], 1.0, A, de, 0.05, gap=2.2)
    des = b.mde_slope_design(sm["design"]["ss_resid"], 1.0, 0.05, de, A)
    dec = b.mde_slope_declared(sm["n_eff_projected"], 0.05, de, A, sm["design"]["vif_w"])
    assert sm["mde_per_sd_c"] == pytest.approx(max(des, dec) * 100) and sm["mde_tercile_c"] == pytest.approx(max(des, dec) * 2.2 * 100)
    assert np.isfinite(sm["design"]["vif_w"]) and sm["design"]["vif_w"] > 1.0
    assert lt.slope_mde(pop, "z", ["c1"], 1.0, A, de, 0.05, gap=float("nan"))["mde_tercile_c"] == float("inf")
    assert lt.slope_mde(pop.iloc[0:0], "z", ["c1"], 1.0, A, de, 0.05, gap=2.2)["mde_tercile_c"] == float("inf")
    assert lt.slope_mde(pop, "z", ["c1"], 1.0, A, float("nan"), 0.05, gap=2.2)["mde_tercile_c"] == float("inf")


def test_f_mde_declared_form_design_and_cap():
    f = lt.f_mde(0.30, 0.6, A)
    assert f["f_mde_c"] == pytest.approx(0.30 * math.sqrt(2 / 0.4)) and f["design_c"] is None
    # r_w <= 0 is floored at 0 (max(0, r_w))
    assert lt.f_mde(0.30, -0.7, A)["f_mde_c"] == pytest.approx(0.30 * math.sqrt(2.0))
    # design-based: max(declared, design)
    big = lt.f_mde(0.10, 0.0, A, design_ss=1e4, scale=1.0, sd=0.05, de_gate=6.196, gap=2.2)
    assert big["f_mde_c"] == max(big["declared_c"], big["design_c"]) and big["design_c"] > big["declared_c"]
    assert lt.f_mde(0.1, 1.0, A)["f_mde_c"] == float("inf")  # r_w = 1: not identified
    assert lt.f_mde(0.1, float("nan"), A)["f_mde_c"] == float("inf") and lt.f_mde(float("inf"), 0.1, A)["f_mde_c"] == float("inf")
    # the 0.5c cap: 0.37c at r_w = 0.5 -> 0.74c > 0.5c fails; 0.20c at r_w = 0.5 -> 0.40c passes
    cap = A["f_mde_max"] * 100
    assert lt.f_mde(0.37, 0.5, A)["f_mde_c"] > cap and lt.f_mde(0.20, 0.5, A)["f_mde_c"] <= cap
    assert cap == pytest.approx(0.5)


def test_contrast_design_is_larger_than_slope_design_when_terms_are_correlated():
    rng = np.random.default_rng(4)
    n_m, per = 200, 20
    df = pd.DataFrame({"market_id": np.repeat([f"m{i}" for i in range(n_m)], per), "t_row": np.tile(np.arange(per) * 7200.0, n_m)})
    z = rng.normal(size=len(df))
    for r, key in ((0.0, "lo"), (0.9, "hi")):
        df[f"a_{key}"] = z
        df[f"b_{key}"] = r * z + math.sqrt(1 - r * r) * rng.normal(size=len(df))
    lo = lt.contrast_ss(df, ["a_lo", "b_lo"], [], "a_lo", "b_lo")["ss_contrast"]
    hi = lt.contrast_ss(df, ["a_hi", "b_hi"], [], "a_hi", "b_hi")["ss_contrast"]
    assert lo > hi > 0  # a correlated pair is harder to tell apart
    assert math.isnan(lt.contrast_ss(df.iloc[:5], ["a_lo", "b_lo"], [], "a_lo", "b_lo")["ss_contrast"])


# --- identification gates ---------------------------------------------------------------------------------------------------------------


def test_residual_iqr_is_taken_after_the_controls_not_raw():
    rng = np.random.default_rng(5)
    rows = []
    for m in range(40):
        for _i in range(10):
            ctl = rng.normal() * 3  # the control carries all the spread
            rows.append({"market_id": f"m{m}", "y": ctl + rng.normal() * 0.01, "ctl": ctl})
    pop = pd.DataFrame(rows)
    r = lt.resid_iqr(pop, "y", ["ctl"], 6, 0.5)
    assert r["share"] == 0.0 and r["raw_share"] == 1.0 and r["markets"] == 40  # raw IQR is large, the residual IQR is not
    g = {"resid_iqr_share_min": 0.5, "resid_iqr_markets_min": 30}
    assert lt.iqr_ok(r, g) is False
    pop["y"] = pop["ctl"] + rng.normal(size=len(pop))
    assert lt.iqr_ok(lt.resid_iqr(pop, "y", ["ctl"], 6, 0.5), g) is True
    few = lt.resid_iqr(pop[pop["market_id"].isin(["m0", "m1"])], "y", ["ctl"], 6, 0.5)
    assert few["markets"] == 2 and lt.iqr_ok(few, g) is False


def test_terciles_and_standardise():
    c, s = lt.standardise([1.0, 2.0, 3.0, np.nan])
    assert c == 2.0 and s == pytest.approx(1.0)
    t1, t2, gap = lt.terciles(np.arange(1.0, 10.0))
    assert gap == pytest.approx(np.mean([7.0, 8.0, 9.0]) - np.mean([1.0, 2.0, 3.0]))
    assert math.isnan(lt.terciles([1.0, 2.0])[2])


def test_family_rule_excludes_a_series_above_40_percent():
    pop = pd.DataFrame({"skey": ["s1"] * 5 + ["s2"] * 3 + ["s3"] * 2, "market_id": list("abcdefghij")})
    out, excl, top = lt._fam(pop, 0.4)
    assert excl == "s1" and top == pytest.approx(0.5) and len(out) == 5
    out2, excl2, _ = lt._fam(pop, 0.6)
    assert excl2 == "" and len(out2) == 10


def test_gate_min_days_nan_fails_every_gate():
    res = {"gate_X": {"a": True, "b": True, "pass": True}}
    out = lt._gate_min_days(res, "gate_X", 1.0, 5.0)
    assert out["gate_X"]["pass"] is False and out["gate_X"]["values_nan"] is True and out["gate_X"]["a"] is False
    res2 = {"gate_X": {"a": True, "pass": True}}
    assert lt._gate_min_days(res2, "gate_X", 5.0, 5.0)["gate_X"]["pass"] is True
    assert lt._gate_min_days({"gate_X": {"a": True}}, "gate_X", float("nan"), 5.0)["gate_X"]["pass"] is False


# --- semantic gate (CV7) ----------------------------------------------------------------------------------------------------------------


def sem_rows(n_traded=60, n_untraded=40, *, traded_above=1.0, untraded_above=0.0, recent=1.0, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for _i in range(n_traded):
        notional = 20.0 + 100.0 * rng.random()
        above = rng.random() < traded_above
        rows.append({"n_int": 2.0, "notional": notional, "covered": True, "covered24": True, "n_prev24": 0.0, "vol_present": True, "dV": (notional * 2 if above else 0.0) + 1.0,
                     "above": above, "recent": rng.random() < recent})
    for _i in range(n_untraded):
        above = rng.random() < untraded_above
        rows.append({"n_int": 0.0, "notional": 0.0, "covered": True, "covered24": True, "n_prev24": 0.0, "vol_present": True, "dV": 50.0 if above else 0.0, "above": above, "recent": False})
    return pd.DataFrame(rows)


def test_semantic_gate_conditions():
    ok = lt.semantic_gate(sem_rows(), SPEC)
    assert ok["gate_CH193_semantic"]["pass"] is True and ok["spearman_dV_notional"] >= 0.5
    # traded share below 70%
    assert lt.semantic_gate(sem_rows(traded_above=0.5), SPEC)["gate_CH193_semantic"]["traded_share"] is False
    # untraded share above 30%
    assert lt.semantic_gate(sem_rows(untraded_above=0.6), SPEC)["gate_CH193_semantic"]["untraded_share"] is False
    # the latency check: fewer than 30 intervals gives NaN, which fails
    few = lt.semantic_gate(sem_rows(recent=0.2, n_traded=60), SPEC)
    assert few["latency_intervals"] < 30 and math.isnan(few["latency_share_above"]) and few["gate_CH193_semantic"]["latency"] is False
    # rank correlation below 0.5
    r = sem_rows()
    r.loc[r["n_int"] > 0, "dV"] = np.random.default_rng(1).random(int((r["n_int"] > 0).sum())) * 100
    assert lt.semantic_gate(r, SPEC)["gate_CH193_semantic"]["spearman"] is False
    # incomplete page coverage and sub-$10 notional take an interval out of both groups
    r2 = sem_rows()
    r2.loc[r2.index[:30], "covered"] = False
    assert lt.semantic_gate(r2, SPEC)["traded_intervals"] == 30
    r3 = sem_rows()
    r3.loc[r3["n_int"] > 0, "notional"] = 5.0
    assert lt.semantic_gate(r3, SPEC)["traded_intervals"] == 0
    # the 24-h-earlier roll-off-free share is printed, not gated
    assert "rolloff_free_share_above_printed" in ok and "rolloff_free_share_above_printed" not in ok["gate_CH193_semantic"]


def test_semantic_rows_interval_coverage_and_latency():
    t_k, t_p = T0, T0 - 7200.0
    ser_k = ser_frame({"a": 0.5, "b": 0.5, "c": 0.5, "d": 0.5}, t=t_k, vol={"a": 1100.0, "b": 1100.0, "c": 1000.0, "d": 1100.0})
    ser_p = ser_frame({"a": 0.5, "b": 0.5, "c": 0.5, "d": 0.5}, t=t_p, vol=1000.0)
    feat = pd.DataFrame({"market_id": list("abcd"), "n_returned": [3, 500, 3, 3]})
    tr = pd.DataFrame({"market_id": ["a", "a", "b", "d", "d", "a"], "ts": [str(t_k - 100), str(t_k - 200), str(t_k - 300), str(t_k - 3000), str(t_k + 50), str(t_k)],
                       "price": ["0.5"] * 6, "size": ["40", "40", "40", "40", "40", "40"]})
    R = lt.semantic_rows(ser_k, ser_p, feat, tr, SPEC)
    # prints at or after t_k are never held (the print at t_k + 50 and at t_k)
    assert R.loc["a", "n_int"] == 2 and R.loc["d", "n_int"] == 1 and R.loc["c", "n_int"] == 0
    assert R.loc["a", "notional"] == pytest.approx(40.0) and bool(R.loc["a", "recent"]) and not bool(R.loc["d", "recent"])
    # market b has a full page (500 rows) whose oldest held row is after t_p: the interval is not covered
    assert not bool(R.loc["b", "covered"]) and bool(R.loc["a", "covered"])
    assert bool(R.loc["a", "above"]) and not bool(R.loc["c", "above"])
