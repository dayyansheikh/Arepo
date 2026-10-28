# ruff: noqa: E501
"""LT12 gate path (LIVE_TESTS_12.md 1.8, R1 must-fix 6, re-check fix 1), synthetic frames only: the expanding-past event x UTC-day demeaning, the
event-clustered CR1 t, the gate sample (events with n_e >= 16) and the observed statistic refitted on it, one offset per event drawn on [s_e, n_e - s_e],
the RAW state shifted (never a demeaned value; a pre-demeaned frame is refused), CH244's interactions recomputed from the shifted shock, the demeaning
re-applied on every draw, the target and the other regressors fixed, and missing positions omitted (never filled)."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import live_tests12 as lt


def _ch245_frame(n_by_event: dict[str, int], seed: int = 3) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for e, n in n_by_event.items():
        st = int(rng.integers(0, 20))
        for i in range(n):
            s = st + i
            rows.append({"event_id": e, "market_id": e + "-t", "slot": s, "day": str(s // 12), "zs": float(rng.normal()), "own_ds_c": float(rng.normal()),
                         "lvl": float(rng.normal()), "y": float(rng.normal())})
    return pd.DataFrame(rows)


def _ch244_frame(seed: int = 5, events: int = 4, n: int = 30, members: int = 4, hole: float = 0.15) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for e in range(events):
        unrew = (np.arange(members) % 2).astype(float)
        for i in range(n):
            for j in range(members):
                if rng.random() < hole:
                    continue  # the member has no unit at this capture
                sh = float(rng.random() < 0.5)
                tl = int(rng.integers(0, 4))
                rows.append({"event_id": f"E{e}", "market_id": f"E{e}-{j}", "slot": i, "day": str(i // 12), "shock": sh, "shock_sz": sh * float(rng.uniform(1, 5)),
                             "unrew": unrew[j], "tl1": float(tl == 1), "tl2": float(tl == 2), "tl3": float(tl == 3), "lowliq": float(rng.random() < 0.5),
                             "own_ds_c": float(rng.normal()), "y": float(rng.normal())})
    df = pd.DataFrame(rows)
    lt._recompute("CH244", df)
    return df


def _sandwich_t(y, X, ev) -> float:
    """Independent CR1 t of the first non-intercept column: full OLS, cluster sandwich, G/(G-1) x (n-1)/(n-k)."""
    n, k = X.shape
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    e = y - X @ beta
    codes, uniq = pd.factorize(np.asarray(ev))
    G = len(uniq)
    meat = np.zeros((k, k))
    for g in range(G):
        m = codes == g
        s = X[m].T @ e[m]
        meat += np.outer(s, s)
    V = XtX_inv @ meat @ XtX_inv * (G / (G - 1)) * ((n - 1) / (n - k))
    return float(beta[1] / math.sqrt(V[1, 1]))


def test_strict_expanding_demean_uses_only_strictly_earlier_captures():
    codes = np.array([0, 0, 0, 0, 1, 1])
    slot = np.array([1, 1, 2, 3, 1, 2], float)
    x = np.array([1.0, 3.0, 5.0, 7.0, 10.0, 20.0])
    d = lt.strict_expanding_demean(codes, slot, x)
    assert np.isnan(d[0]) and np.isnan(d[1]) and np.isnan(d[4])  # first capture of each stratum drops (both units of slot 1)
    assert d[2] == pytest.approx(5.0 - 2.0) and d[3] == pytest.approx(7.0 - 3.0) and d[5] == pytest.approx(10.0)
    # causal: changing a later value never changes an earlier demeaned value
    x2 = x.copy()
    x2[3] = 1e6
    d2 = lt.strict_expanding_demean(codes, slot, x2)
    assert d2[2] == d[2] and d2[5] == d[5]


def test_cr1_event_t_matches_an_independent_sandwich():
    rng = np.random.default_rng(11)
    n = 400
    ev = rng.integers(0, 25, n)
    x, z = rng.normal(size=n), rng.normal(size=(n, 2))
    y = 0.3 * x + z @ np.array([0.5, -0.2]) + rng.normal(size=n) + 0.5 * rng.normal(size=25)[ev]
    r = lt.cr1_event_t(y, x, z, ev)
    X = np.column_stack([np.ones(n), x, z])
    assert r["testable"] and r["t"] == pytest.approx(_sandwich_t(y, X, ev), rel=1e-9)


def test_gate_refuses_a_pre_demeaned_frame():
    df = _ch245_frame({"a": 40, "b": 40})
    D = lt.demeaned_frame(df, ["zs", "own_ds_c"])
    with pytest.raises(AssertionError, match="RAW states only"):
        lt.event_day_state_shift_gate(D, D["y"].to_numpy(), "zs", ["own_ds_c"], test="CH245", draws=3, seed=1)


def test_shifting_demeaned_values_is_not_the_same_design():
    """The fixture of 8.3 / 1.8: an event spanning several UTC days; shifting pre-demeaned values carries other days' stratum means into this day, so the
    design differs from shifting the RAW state and re-applying the demeaning (the gate's path; a pre-demeaned frame is refused above)."""
    df = _ch245_frame({"a": 48})
    codes, slot = lt.stratum_codes(df), df["slot"].to_numpy(float)
    raw = df["zs"].to_numpy(float) + np.repeat([0.0, 5.0, -3.0, 9.0], 12)  # day-level means differ
    o = 13
    src = (np.arange(48) + o) % 48
    gate_path = lt.strict_expanding_demean(codes, slot, raw[src])
    shifted_demeaned = lt.strict_expanding_demean(codes, slot, raw)[src]
    ok = np.isfinite(gate_path) & np.isfinite(shifted_demeaned)
    assert ok.sum() > 20 and not np.allclose(gate_path[ok], shifted_demeaned[ok])


def test_event_phase_index_rule_and_gate_sample_minimum():
    df = _ch245_frame({"short8": 8, "short15": 15, "e16": 16, "e40": 40})
    idx = lt.event_phase_index(df, np.arange(len(df)), 16)
    assert set(idx["plan"]) == {"e16", "e40"} and idx["excluded_events"] == 2 and idx["excluded_rows"] == 23
    assert idx["plan"]["e16"]["s_e"] == 4 and idx["plan"]["e40"]["s_e"] == 10 and idx["plan"]["e40"]["n_e"] == 40


def test_gate_statistic_is_the_cr1_t_refitted_on_the_gate_sample():
    """Re-check fix 1: events with n_e < 16 are excluded from the gate (counted) and the OBSERVED statistic is the event-clustered CR1 t refitted on that
    same gate sample (never the all-units primary fit)."""
    df = _ch245_frame({"s1": 8, "s2": 12, "s3": 10, "a": 30, "b": 36, "c": 44, "d": 20}, seed=8)
    df.loc[df["event_id"].isin(["s1", "s2", "s3"]), "y"] += 3.0 * df.loc[df["event_id"].isin(["s1", "s2", "s3"]), "zs"]  # short events carry a slope
    ctrl = ["own_ds_c", "lvl"]
    g = lt.event_day_state_shift_gate(df, df["y"].to_numpy(), "zs", ctrl, test="CH245", draws=9, seed=4)
    assert g["testable"] and g["excluded_events"] == 3 and g["events_shifted"] == 4 and g["gate_rows"] == 130
    G = df[~df["event_id"].isin(["s1", "s2", "s3"])].reset_index(drop=True)
    D = lt.demeaned_frame(G, ["zs", *ctrl])
    ok = np.all(np.isfinite(D[["zs", *ctrl]].to_numpy(float)), axis=1)
    X = np.column_stack([np.ones(ok.sum()), D.loc[ok, ["zs", *ctrl]].to_numpy(float)])
    t_gate = _sandwich_t(G.loc[ok, "y"].to_numpy(float), X, G.loc[ok, "event_id"].to_numpy())
    assert g["t_obs"] == pytest.approx(t_gate, rel=1e-9)
    Dall = lt.demeaned_frame(df, ["zs", *ctrl])
    okA = np.all(np.isfinite(Dall[["zs", *ctrl]].to_numpy(float)), axis=1)
    XA = np.column_stack([np.ones(okA.sum()), Dall.loc[okA, ["zs", *ctrl]].to_numpy(float)])
    t_all = _sandwich_t(df.loc[okA, "y"].to_numpy(float), XA, df.loc[okA, "event_id"].to_numpy())
    assert abs(t_all - g["t_obs"]) > 0.5  # the all-units fit is a different statistic
    assert g["p_perm"] * 10 == pytest.approx(round(g["p_perm"] * 10)) and g["statistic"].startswith("event-clustered CR1 t")


def test_one_offset_per_event_and_the_raw_state_is_circularly_shifted():
    df = _ch245_frame({"a": 40, "b": 33, "c": 50, "short": 9}, seed=2)
    seen = []
    lt.event_day_state_shift_gate(df, df["y"].to_numpy(), "zs", ["own_ds_c"], test="CH245", draws=6, seed=9, trace=seen.append)
    assert len(seen) == 6
    for tr in seen:
        G, src, pos, offs, ev = tr["G"], tr["src"], tr["pos"], tr["offsets"], tr["events"]
        assert "short" not in set(G["event_id"])
        codes, slot = lt.stratum_codes(G), G["slot"].to_numpy(float)
        for i_e, e in enumerate(ev):
            m = np.flatnonzero(G["event_id"].to_numpy() == e)
            n_e = len(m)
            s_e = max(4, math.ceil(n_e / 4))
            o = int(offs[i_e])
            assert s_e <= o <= n_e - s_e
            assert np.array_equal(pos[src[m]], (pos[m] + o) % n_e)  # every unit of the event moved by the SAME offset
            assert set(G["event_id"].to_numpy()[src[m]]) == {e}  # never borrowed from another event
        # the shifted column is the raw state re-demeaned in each unit's real stratum and order; the target / other regressors keep analysis values
        assert np.allclose(tr["Dm"]["zs"].to_numpy(float), lt.strict_expanding_demean(codes, slot, G["zs"].to_numpy(float)[src]), equal_nan=True)
        assert np.allclose(tr["Dm"]["own_ds_c"].to_numpy(float), tr["D"]["own_ds_c"].to_numpy(float), equal_nan=True)


def test_ch244_shift_recomputes_interactions_and_omits_missing_positions():
    df = _ch244_frame()
    ctrl = ["unrew", "shock", "shock_sz", "tl1", "tl2", "tl3", "tl1_x_shock", "tl2_x_shock", "tl3_x_shock", "own_ds_c"]
    seen = []
    g = lt.event_day_state_shift_gate(df, df["y"].to_numpy(), "shock_x_unrew", ctrl, test="CH244", draws=4, seed=3, trace=seen.append)
    assert g["testable"] and g["omitted_share_max"] > 0
    for tr in seen:
        G, src, Dm, D = tr["G"], tr["src"], tr["Dm"], tr["D"]
        codes, slot = lt.stratum_codes(G), G["slot"].to_numpy(float)
        keep = src >= 0
        # a member lacking a unit at the shifted position is omitted (NaN), never filled or borrowed from another member
        assert np.isnan(Dm["shock"].to_numpy(float)[~keep]).all()
        assert (G["market_id"].to_numpy()[src[keep]] == G["market_id"].to_numpy()[keep]).all()
        sh = np.full(len(G), np.nan)
        sh[keep] = G["shock"].to_numpy(float)[src[keep]]
        sz = np.full(len(G), np.nan)
        sz[keep] = G["shock_sz"].to_numpy(float)[src[keep]]  # shock_size shifts with shock (ruling B3)
        assert np.allclose(Dm["shock_sz"].to_numpy(float), lt.strict_expanding_demean(codes, slot, sz), equal_nan=True)
        exp = lt.strict_expanding_demean(codes, slot, sh * G["unrew"].to_numpy(float))  # recomputed with the unit's OWN unrew
        assert np.allclose(Dm["shock_x_unrew"].to_numpy(float), exp, equal_nan=True)
        exp1 = lt.strict_expanding_demean(codes, slot, sh * G["tl1"].to_numpy(float))
        assert np.allclose(Dm["tl1_x_shock"].to_numpy(float), exp1, equal_nan=True)
        for c in ("unrew", "tl1", "own_ds_c"):
            assert np.allclose(Dm[c].to_numpy(float), D[c].to_numpy(float), equal_nan=True)


def test_observed_statistic_is_the_identity_shift():
    """LT12 ambiguity A25: the observed fit goes through the same path as a draw with o = 0 (identity source rows)."""
    df = _ch244_frame(seed=7)
    rng = np.random.default_rng(1)
    df.loc[rng.random(len(df)) < 0.15, "own_ds_c"] = np.nan  # non-units (a fixed control missing) whose shock is finite
    ctrl = ["unrew", "shock", "shock_sz", "own_ds_c"]
    reg = ["shock_x_unrew", *ctrl]
    g = lt.event_day_state_shift_gate(df, df["y"].to_numpy(), "shock_x_unrew", ctrl, test="CH244", draws=2, seed=3)
    units = np.all(np.isfinite(df[reg].to_numpy(float)), axis=1)
    G = df[units].reset_index(drop=True)
    D = lt.demeaned_frame(df, reg)[units].reset_index(drop=True)  # fixed regressors: analysis values
    codes, slot = lt.stratum_codes(G), G["slot"].to_numpy(float)
    for c in ("shock_x_unrew", "shock", "shock_sz"):  # the shifted columns: re-demeaned over the gate sample, as in every draw
        D[c] = lt.strict_expanding_demean(codes, slot, G[c].to_numpy(float))
    ok = np.all(np.isfinite(D[reg].to_numpy(float)), axis=1)
    X = np.column_stack([np.ones(ok.sum()), D.loc[ok, reg].to_numpy(float)])
    assert g["t_obs"] == pytest.approx(_sandwich_t(G.loc[ok, "y"].to_numpy(float), X, G.loc[ok, "event_id"].to_numpy()), rel=1e-9)


def test_p_perm_is_one_plus_exceedances_over_one_plus_draws():
    df = _ch245_frame({"a": 40, "b": 36, "c": 44}, seed=1)
    g = lt.event_day_state_shift_gate(df, df["y"].to_numpy(), "zs", ["own_ds_c"], test="CH245", draws=19, seed=2)
    k = round(g["p_perm"] * 20)
    assert 1 <= k <= 20 and g["p_perm"] == pytest.approx(k / 20) and g["passes"] == (g["p_perm"] < 0.05)
    g2 = lt.event_day_state_shift_gate(df, df["y"].to_numpy(), "zs", ["own_ds_c"], test="CH245", draws=19, seed=2)
    assert g2["p_perm"] == g["p_perm"]  # deterministic for a seed


def test_nan_draw_statistics_count_as_exceedances(monkeypatch):
    """Code-freeze check fix 4: a draw whose statistic is NaN counts as an exceedance (conservative), never as a non-exceedance."""
    df = _ch245_frame({"a": 40, "b": 36, "c": 44}, seed=1)
    real, calls = lt.cr1_event_t, []

    def first_only(*a, **k):
        calls.append(1)
        return real(*a, **k) if len(calls) == 1 else {"testable": False, "t": float("nan")}  # the observed fit is real; every draw is NaN

    monkeypatch.setattr(lt, "cr1_event_t", first_only)
    g = lt.event_day_state_shift_gate(df, df["y"].to_numpy(), "zs", ["own_ds_c"], test="CH245", draws=19, seed=2)
    assert g["testable"] is True and g["draw_t_nan"] == 19 and g["p_perm"] == pytest.approx(1.0) and g["passes"] is False


def test_gate_without_a_long_event_is_not_testable():
    df = _ch245_frame({"a": 10, "b": 12})
    g = lt.event_day_state_shift_gate(df, df["y"].to_numpy(), "zs", ["own_ds_c"], test="CH245", draws=3, seed=1)
    assert g["testable"] is False and g["passes"] is False
