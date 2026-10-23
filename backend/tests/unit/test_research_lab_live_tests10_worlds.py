# ruff: noqa: E501
"""LT10 simulated worlds and the size check (LIVE_TESTS_10.md 1.8, 1.8.1): the structure of W1-W10, the reader's own builders on a world, the criterion, the
scenario-to-test map (fail-closed), the declared consequence of a failure, and the CLI. Small worlds only (the registered run is 2,000 worlds x 200 draws)."""

from __future__ import annotations

import copy
import types

import numpy as np
import pytest

from astrolabe.research_lab import live_tests10 as lt
from astrolabe.research_lab import live_tests10_analysis as an
from astrolabe.research_lab import live_tests10_worlds as W

SMALL = dict(plan=[1, 1, 2, 2, 3], days=3)


def sim(world, seed=1, **kw):
    return W.simulate(world, np.random.default_rng(seed), **kw)


def test_standard_structure_w1():
    S = sim("W1")
    assert S["P"] == 60 and len(S["plan"]) == 30 and S["n"] == 7 * 720 and S["days"] == 7
    assert sorted(set(S["plan"])) == [1, 2, 3, 4] and [S["plan"].count(k) for k in (1, 2, 3, 4)] == [12, 9, 6, 3]
    assert abs(float((S["pt"] == 0.001).mean()) - 0.10) < 0.2 and set(np.unique(S["pt"])) <= {0.001, 0.01}
    A = S["A"]
    assert A["present"].all() and np.isfinite(A["k_bid"]).all() and (A["k_ask"] > A["k_bid"]).all() and (A["p_ask"] > A["p_bid"]).all()
    assert (np.abs(np.round(A["k_bid"] / 0.01) * 0.01 - A["k_bid"]) < 1e-9).all()  # Kalshi on a 1c tick
    assert (S["cols"] % 5 == 0).all() and (W.T_BASE + 120 * S["cols"][0]) % 600 == 0 and S["cols"][0] >= 32
    assert (S["pair_st"] == lt.ST["unit"]).all()


def test_standard_vs_big_plans():
    assert sum(W.STD_PLAN) == 60 and len(W.STD_PLAN) == 30 and sum(W.BIG_PLAN) == 84 and len(W.BIG_PLAN) == 65
    assert lt.g_eff([e for e, k in enumerate(W.BIG_PLAN) for _ in range(k)]) == pytest.approx(84**2 / (400 + 64))


def test_simulation_is_deterministic_per_seed():
    a, b = sim("W2", 7, **SMALL), sim("W2", 7, **SMALL)
    assert np.array_equal(a["A"]["k_bid"], b["A"]["k_bid"]) and np.array_equal(a["A"]["p_ask"], b["A"]["p_ask"])
    assert not np.array_equal(a["A"]["k_bid"], sim("W2", 8, **SMALL)["A"]["k_bid"])


def test_w3_polymarket_follows_kalshi_with_a_two_poll_lag():
    def mse(S, shift):
        x = S["x"]
        pmid = (S["A"]["p_bid"] + S["A"]["p_ask"]) / 2
        xs = np.concatenate([np.repeat(x[:, :1], shift, axis=1), x[:, : x.shape[1] - shift]], axis=1) if shift else x
        return float(np.mean((pmid[:, 10:] - xs[:, 10:]) ** 2))

    S1, S3 = sim("W1", 3, plan=[1] * 12, days=4), sim("W3", 3, plan=[1] * 12, days=4)
    assert mse(S3, 2) < mse(S3, 0) and mse(S1, 0) < mse(S1, 2)  # W3: x_{t-2}; W1: simultaneous with x_t
    km = (S3["A"]["k_bid"] + S3["A"]["k_ask"]) / 2
    assert float(np.mean((km[:, 10:] - S3["x"][:, 10:]) ** 2)) < mse(S3, 0) + 0.01  # Kalshi's mid carries x_t


def test_w4_klast_resets_on_a_venue_cadence():
    S2, S4 = sim("W3", 4, **SMALL), sim("W4", 4, **SMALL)
    ch2 = (np.diff(S2["A"]["k_last"], axis=1) != 0).mean()
    ch4 = (np.diff(S4["A"]["k_last"], axis=1) != 0).mean()
    assert ch4 > ch2 + 0.03  # the reset every 15th poll (and at 30% of hours) changes k_last without a trade
    j = np.arange(S4["n"])
    at15 = (j % 15 == 0)[1:]
    assert (np.diff(S4["A"]["k_last"], axis=1) != 0)[:, at15].mean() > (np.diff(S4["A"]["k_last"], axis=1) != 0)[:, ~at15].mean()


def test_w5_activity_sets_the_lag_and_the_trade_rate():
    S3, S5 = sim("W3", 5, **SMALL), sim("W5", 5, **SMALL)
    assert not np.array_equal(S3["A"]["p_bid"], S5["A"]["p_bid"])
    tr3 = (np.diff(S3["A"]["k_vol24"], axis=1) > 20).mean()
    tr5 = (np.diff(S5["A"]["k_vol24"], axis=1) > 20).mean()
    assert tr5 != tr3


def test_w6_bot_resets_kalshi_sizes_every_five_polls():
    S1, S6 = sim("W1", 6, **SMALL), sim("W6", 6, **SMALL)
    r = S6["A"]["k_bid_sz"] / S1["A"]["k_bid_sz"]  # same seed: only the bot factor differs
    assert np.nanmin(r) == pytest.approx(0.3, abs=0.02) and np.nanmax(r) == pytest.approx(1.0, abs=0.02)
    j = np.arange(S6["n"])
    for i in range(3):
        phase = int(np.argmin([np.nanmean(r[i][(j % 5) == k]) for k in range(5)]))
        assert np.nanmean(r[i][(j % 5) == phase]) == pytest.approx(0.3, abs=0.03)


def test_w7_withdrawals_in_quiet_windows_grow_with_volatility():
    S = sim("W7", 7, plan=[1] * 8, days=4)
    S2 = sim("W2", 7, plan=[1] * 8, days=4)
    # W7 = W2 plus withdrawals (a two-tick widening or a size fall to 40%): more sampled-poll widenings and size falls than W2
    sw = lambda s: ((s["A"]["k_ask"] - s["A"]["k_bid"]) >= 0.0399).mean()  # noqa: E731
    assert sw(S) > sw(S2) - 1e-12
    assert np.nanmin(S["A"]["k_bid_sz"] / S2["A"]["k_bid_sz"]) < 0.5


def test_w8_alternative_spread_processes():
    S1, S8 = sim("W1", 8, **SMALL), sim("W8", 8, **SMALL)
    sk = np.round((S8["A"]["k_ask"] - S8["A"]["k_bid"]) / 0.01)
    assert sk.min() >= 1 and sk.max() <= 10
    chg = (np.diff(sk, axis=1) != 0).mean()
    assert 0.05 < chg < 0.12  # step probability 0.1 less the reflecting boundary
    sk1 = np.round((S1["A"]["k_ask"] - S1["A"]["k_bid"]) / 0.01)
    assert (np.diff(sk, axis=1) != 0).mean() < (np.diff(sk1, axis=1) != 0).mean()


def test_w9_common_slow_spread_drift():
    S1, S9 = sim("W1", 9, plan=[1] * 10, days=5), sim("W9", 9, plan=[1] * 10, days=5)

    def lowfreq_corr(S):
        s = (S["A"]["k_ask"] - S["A"]["k_bid"]) / 0.01
        b = s.reshape(S["P"], -1, 360).mean(axis=2)  # 12-hour means
        c = np.corrcoef(b)
        return float(c[np.triu_indices(S["P"], 1)].mean())

    assert lowfreq_corr(S9) > lowfreq_corr(S1) + 0.05


def test_w10_large_event_contiguous_presence_and_jump_widening():
    S = sim("W10", 10)
    assert S["P"] == 84 and len(S["plan"]) == 65 and S["days"] == 21 and S["n"] == 21 * 720
    ent, ret, n = S["entry"], S["retire"], S["n"]
    part = np.flatnonzero((ent > -10**8) | (ret < n))
    assert len(part) <= 21 and (S["ev_of"][part] == 0).sum() <= 5
    pres = S["A"]["present"]
    for p in part[:5]:
        j = np.flatnonzero(pres[p])
        assert j.min() == ent[p] and j.max() == min(ret[p] + W.RETIRE_POLLS, n - 1) and (np.diff(j) == 1).all()  # contiguous
        st = S["pair_st"][p]
        cols = S["cols"]
        assert (st[cols < ent[p] + W.L_POLLS] == lt.ST["not_yet_in_force"]).all() and (st[cols > ret[p]] == lt.ST["retired"]).all()
    assert W.L_POLLS == 95 and W.RETIRE_POLLS == 190
    # at an event jump poll both spreads widen
    j_ev = np.argwhere(S["jump_flag"])[:30]
    d = []
    for e, jj in j_ev:
        if 6 <= jj < n - 3:
            p = np.flatnonzero(S["ev_of"] == e)[0]
            d.append((S["A"]["k_ask"][p, jj + 1] - S["A"]["k_bid"][p, jj + 1]) - (S["A"]["k_ask"][p, jj - 5] - S["A"]["k_bid"][p, jj - 5]))
    assert np.nanmean(d) > 0


def test_origin_frame_uses_the_readers_builder_and_drops_15_percent():
    S = sim("W1", 11, **SMALL)
    u, tw = W.origin_frame(S, np.random.default_rng(11))
    total = S["P"] * len(S["cols"])
    assert 0.78 * total <= len(u) * 1.0 / 0.85 * 0.85 and len(u) <= 0.88 * total and len(u) == len(tw)
    assert (u["status"] == lt.ST["unit"]).all() and {"dsK", "pull", "cls223", "cls222", "tg_status", "pmid_h", "sP_h"} <= set(u.columns)
    for t in lt.TESTS:
        X, y = W.test_frame(u, tw, t, None)
        assert len(X) == len(y) and np.isfinite(y).any() and lt.TERM[t] in X and "block2" in X
        if t == "CH223":
            assert (X["cls223"] == 0).all() and np.nanmin(y) >= 0
        if t == "CH222":
            assert X["cls222"].isin([0, 1]).all()


def test_w10_status_counts_in_origin_frame():
    S = sim("W10", 12, plan=[3] + [1] * 6, days=5)
    meta_st = S["pair_st"]
    u, _ = W.origin_frame(S, np.random.default_rng(1))
    assert len(u) <= int((meta_st == lt.ST["unit"]).sum())


def test_limit_formula():
    assert an.limit_for(2000) == pytest.approx(0.058, abs=0.0005)
    assert an.limit_for(200) > an.limit_for(2000)


def test_scenario_map_matches_the_design_table():
    S = an.SCENARIOS
    assert set(S) == set(an.SCENARIO_ORDER) == set(W.WORLDS)
    assert S["W4"]["tests"] == ("CH222",) and S["W5"]["tests"] == ("CH222",) and S["W6"]["tests"] == ("CH223",) and S["W7"]["tests"] == ("CH223",)
    assert S["W8"]["tests"] == ("CH224",) and S["W9"] == {"stats": ("verdict",), "tests": ("CH224",)}
    assert S["W10"]["stats"] == ("gate", "verdict") and set(S["W10"]["tests"]) == set(lt.TESTS) and set(S["W1"]["tests"]) == set(lt.TESTS)


def _res(**cells):
    return {t: {k: {"scenario": k.split(":")[0], "stat": k.split(":")[1], "worlds": 2000, "rejections": 0, "rate": r, "limit": 0.058, "ok": r <= 0.058} for k, r in d.items()}
            for t, d in cells.items()}


def test_per_test_result_is_fail_closed_and_per_test():
    full = {k: 0.05 for sc, s in an.SCENARIOS.items() for st in s["stats"] for k in [f"{sc}:{st}"]}
    res = _res(CH224={k: v for k, v in full.items() if "CH224" in an.SCENARIOS[k.split(":")[0]]["tests"]},
               CH223={k: v for k, v in full.items() if "CH223" in an.SCENARIOS[k.split(":")[0]]["tests"]},
               CH222={k: v for k, v in full.items() if "CH222" in an.SCENARIOS[k.split(":")[0]]["tests"]})
    out = an.per_test_result(res, {}, list(lt.TESTS), 2000)
    assert {t: v["status"] for t, v in out.items()} == {t: "pass" for t in lt.TESTS}
    # world 5 fails: only CH222 (the only test bound to it) is 'size scenario'; k is unchanged
    res["CH222"]["W5:gate"] = {**res["CH222"]["W5:gate"], "rate": 0.2, "ok": False}
    out = an.per_test_result(res, {}, list(lt.TESTS), 2000)
    assert out["CH222"]["status"] == "fail_size_scenario" and out["CH222"]["failed_size"] == ["W5:gate"] and out["CH224"]["status"] == "pass" and out["CH223"]["status"] == "pass"
    # world 9 (verdict size) fails: mechanical world, CH224 only
    res["CH224"]["W9:verdict"] = {**res["CH224"]["W9:verdict"], "rate": 0.3, "ok": False}
    out = an.per_test_result(res, {}, list(lt.TESTS), 2000)
    assert out["CH224"]["status"] == "fail_mechanical_world" and out["CH224"]["failed_mechanical"] == ["W9:verdict"]
    # world 10 binds twice: the gate rate -> size scenario; the verdict size -> mechanical world
    res["CH223"]["W10:verdict"] = {**res["CH223"]["W10:verdict"], "rate": 0.3, "ok": False}
    assert an.per_test_result(res, {}, list(lt.TESTS), 2000)["CH223"]["status"] == "fail_mechanical_world"
    res["CH223"]["W10:gate"] = {**res["CH223"]["W10:gate"], "rate": 0.3, "ok": False}
    assert an.per_test_result(res, {}, list(lt.TESTS), 2000)["CH223"]["status"] == "fail_size_scenario"
    # a missing or incomplete statistic fails the test; an unknown scenario is refused
    del res["CH224"]["W1:gate"]
    out = an.per_test_result(res, {}, list(lt.TESTS), 2000)
    assert out["CH224"]["status"] == "fail_size_scenario" and "W1:gate" in out["CH224"]["missing"]
    res["CH222"]["W1:gate"] = {**res["CH222"]["W1:gate"], "worlds": 1999}
    assert "W1:gate" in an.per_test_result(res, {}, list(lt.TESTS), 2000)["CH222"]["missing"]
    with pytest.raises(an.Refused):
        an.per_test_result(res, {}, ["CH224"], 2000, scenarios=("W1", "W99"))
    # the analytic p's own rate in the null worlds sets the label only
    over = an.per_test_result(_res(CH224={"W1:gate": 0.05}), {"CH224": {"W2": {"over_limit": True, "rate": 0.1, "worlds": 5}}}, ["CH224"], 2000, scenarios=("W1",))
    assert over["CH224"]["analytic_oversized"] and over["CH224"]["analytic_over_in"] == ["W2"]


def test_size_check_small_run_end_to_end():
    spec = copy.deepcopy(lt.load_spec(sha=None))
    out = an.size_check(worlds=2, draws=8, seed=777, spec=spec, tests=["CH224", "CH222"], scenarios=("W1", "W4", "W9", "W10"), **SMALL)
    assert out["limit"] == pytest.approx(an.limit_for(2))
    assert set(out["scenarios"]["CH224"]) == {"W1:gate", "W9:verdict", "W10:gate", "W10:verdict"}
    assert set(out["scenarios"]["CH222"]) == {"W1:gate", "W4:gate", "W10:gate", "W10:verdict"}
    for d in out["scenarios"].values():
        for cell in d.values():
            assert cell["worlds"] == 2 and 0 <= cell["rate"] <= 1
    assert "CH223" not in out["scenarios"] and set(out["per_test"]) == {"CH224", "CH222"}
    assert out["per_test"]["CH224"]["status"] in ("pass", "fail_size_scenario", "fail_mechanical_world")
    assert set(out["f_arm_rates_reported"]["CH224"]) == {"W1"}
    # the same seed gives the same result; a different seed does not necessarily
    out2 = an.size_check(worlds=2, draws=8, seed=777, spec=spec, tests=["CH224", "CH222"], scenarios=("W1", "W4", "W9", "W10"), **SMALL)
    assert out == out2


def test_power_runs_are_reported_and_never_bind():
    spec = copy.deepcopy(lt.load_spec(sha=None))
    out = an.size_check(worlds=2, draws=6, seed=777, spec=spec, tests=["CH223"], scenarios=("W6",), power_worlds=2, **SMALL)
    pr = out["power_runs"]["CH223"]
    assert pr["binding"] is False and pr["worlds"] == 2 and 0 <= pr["gate_power"] <= 1 and pr["effect"] == "0.5c between classes"
    assert out["per_test"]["CH223"]["status"] in ("pass", "fail_size_scenario")  # power does not enter the status
    assert an.POWER["CH224"][2] == 41 and an.POWER["CH223"][2] == 42 and an.POWER["CH222"][2] == 43


def test_size_check_cli(tmp_path):
    args = types.SimpleNamespace(out=tmp_path / "size.json", worlds=2, draws=4, dev=True, power_worlds=0)
    written = {}

    def w(path, txt):
        written["txt"] = txt
        return 0

    # the registered plan is large: only check the refusals and the dev path with tiny worlds through the module function
    assert an.size_check_cli(types.SimpleNamespace(out=tmp_path / "s.json", worlds=1, draws=4, dev=True, power_worlds=0), w) == 2
    assert args.dev and "txt" not in written


def test_registered_seed_is_refused_outside_the_registered_run():
    spec = copy.deepcopy(lt.load_spec(sha=None))
    with pytest.raises(an.Refused, match="20261397"):
        an.size_check(worlds=2, draws=4, seed=20261397, spec=spec, tests=["CH223"], scenarios=("W6",), **SMALL)
    assert an.DEV_SEED == 20261397 * 100 + 99
    out = an.size_check(worlds=2, draws=4, seed=20261397, spec=spec, tests=["CH223"], scenarios=("W6",), registered=True, **SMALL)
    assert out["seed_kind"] == "registered" and any("W6 disclosure" in n for n in out["notes"])


def test_cli_dev_uses_the_dev_seed_and_registered_refuses_unfilled(tmp_path):
    seen = {}
    real = an.size_check
    an.size_check = lambda **kw: seen.update(kw) or {"x": 1}
    try:
        w = lambda path, txt: 0  # noqa: E731
        assert an.size_check_cli(types.SimpleNamespace(out=tmp_path / "a", worlds=2, draws=2, dev=True, power_worlds=0), w) == 0
        assert seen["seed"] == an.DEV_SEED and seen["registered"] is False
        assert an.size_check_cli(types.SimpleNamespace(out=tmp_path / "b", worlds=None, draws=None, dev=False, power_worlds=0), w) == 2  # k_tests null in the draft spec
    finally:
        an.size_check = real


def test_analytic_oversize_judged_on_w1_w2_w3_w10():
    assert an.ANALYTIC_OVERSIZE_WORLDS == ("W1", "W2", "W3", "W10") and an.NULL_WORLDS_ANALYTIC == ("W1", "W2", "W3")
    res = _res(CH224={"W10:gate": 0.05, "W10:verdict": 0.05})
    out = an.per_test_result(res, {"CH224": {"W10": {"over_limit": True, "rate": 0.1, "worlds": 5}}}, ["CH224"], 2000, scenarios=("W10",))
    assert out["CH224"]["analytic_oversized"]
