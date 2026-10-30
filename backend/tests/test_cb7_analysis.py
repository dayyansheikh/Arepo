# ruff: noqa: E501
"""CB7 analysis code (cb7_astats, cb7_g_analysis, cb7_x_analysis, cb7_s_analysis, cb7_declaration, run_cb7.py screen / write-spec).

Synthetic fixtures only (no host data): every table is built in the columns the real fetch / census code writes, and the screens are driven through the same
functions and the runner the host uses. Nothing here is evidence."""

from __future__ import annotations

import csv
import gzip
import importlib.util
import json
import time
from pathlib import Path

import numpy as np
import pytest

from astrolabe.research_lab import battery2, h5_seal
from astrolabe.research_lab import cb7_astats as st
from astrolabe.research_lab import cb7_census as cc
from astrolabe.research_lab import cb7_common as cm
from astrolabe.research_lab import cb7_declaration as D
from astrolabe.research_lab import cb7_g_analysis as G
from astrolabe.research_lab import cb7_s_analysis as S
from astrolabe.research_lab import cb7_x_analysis as X
from astrolabe.research_lab import cb7_xv as xv

BACKEND = Path(__file__).resolve().parents[1]


def _runner():
    spec = importlib.util.spec_from_file_location("run_cb7_under_test", BACKEND / "scripts" / "run_cb7.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


RUN = _runner()


def _out(capsys) -> dict:
    lines = [x for x in capsys.readouterr().out.strip().splitlines() if x.startswith("{")]
    return json.loads(lines[-1]) if lines else {}


# ---- G fixtures ------------------------------------------------------------------------------------------------------------------------

END0 = 1_760_000_000
DAY = 86400.0


def g_tables(n_ev=400, yes=range(0, 400, 5), m=0.05, fee_cat="other:foo", question="Will a ceasefire be signed in zone {i}?", early=()):
    """sample rows / origin_prices rows / guarded outcomes in the columns the h8_geo fetch writes (one market per event, origin k = 14)."""
    rows, prices, outcomes = [], [], {}
    yes = set(yes)
    for i in range(n_ev):
        end = END0 + i * 43200
        close = end - 3 * DAY if i in early else end
        rows.append({"market_id": str(i), "event_id": str(i), "event_ids": str(i), "neg_risk_market_id": "", "question": question.format(i=i), "event_title": "", "slug": "",
                     "fee_category": fee_cat, "end_epoch": str(end), "close_epoch": str(close), "closed_after_cap": "0", "market_tag_ids": "100265", "event_tag_ids": "", "status": "closed"})
        prices.append({"market_id": str(i), "k": "14", "origin_ts": str(end - 14 * DAY), "m": str(m), "eligible": "1"})
        outcomes[str(i)] = '["1","0"]' if i in yes else '["0","1"]'
    return rows, prices, outcomes


def g_units(**kw):
    rows, prices, outcomes = g_tables(**kw)
    units0 = G.build_units(rows, prices, set())
    return G.attach_outcomes(units0, outcomes)


K_005 = (0.05 + 0.015) + 0.07 * (0.05 + 0.015) * (1 - (0.05 + 0.015))  # a + f at m = 0.05, unknown fee rate 0.07


def test_cost_model_and_fee_rate():
    assert G.fee_rate_g("geopolitics") == 0.0
    assert G.fee_rate_g("other:foo") == 0.07 and G.fee_rate_g("") == 0.07 and G.fee_rate_g(None) == 0.07
    assert G.fee_rate_g("politics") == 0.04
    assert G.ask_of(0.05) == pytest.approx(0.065) and G.ask_of(0.04) == pytest.approx(0.0605)
    assert G.ask_of(0.995) == 0.999  # cap
    assert G.ask_of(0.05, shift=0.0075) == pytest.approx(0.0725)
    assert G.ask_of(0.05, h_floor=0.03) == pytest.approx(0.08)


def test_g1_known_answer_effect():
    units, unres = g_units()
    assert len(units) == 400 and not unres
    t = G.g1_test(units)
    assert t["mean"] == pytest.approx(0.2 - K_005)
    assert t["testable"] and t["p"] < 1e-6 and t["yes_event_clusters"] == 80
    assert t["r_ann"] == pytest.approx(365 * (0.2 - K_005) / (K_005 * 14))
    assert G.floor_ok(t)


def test_g1_null_is_not_detected():
    units, _ = g_units(yes=range(0, 400, 14))  # 29 / 400 = 7.25% against a + f = 6.93%
    t = G.g1_test(units)
    assert t["testable"] and t["p"] > 0.1 and not G.floor_ok(t)


def test_g1_fewer_than_10_yes_clusters_is_not_testable_p1():
    units, _ = g_units(yes=range(0, 45, 10))  # 5 YES events
    t = G.g1_test(units)
    assert t["yes_event_clusters"] == 5 and not t["testable"] and t["p"] == 1.0
    assert not G.inverted_tail_gate(units)["passes"]


def test_theme_way_below_15_is_not_testable():
    q = "Will Russia attack zone {i}?"  # every unit in the same theme: 1 theme cluster
    units, _ = g_units(question=q)
    t = G.g1_test(units)
    assert not t["testable"] and t["p"] == 1.0 and any("theme" in r for r in t["reason"])


def test_inverted_tail_gate_lower_bound_and_half_wins():
    hi, _ = g_units()  # 20% against 6.9%
    g = G.inverted_tail_gate(hi)
    assert g["passes"] and g["lower_bound"] > g["required"] and g["testable"]
    lo, _ = g_units(yes=range(0, 400, 12))  # 34 / 400 = 8.5%: net positive, lower bound below pi* + 0.5pp
    g = G.inverted_tail_gate(lo)
    assert g["testable"] and not g["passes"] and g["lower_bound"] < g["required"]
    # 50-50 counts half in pi but is not a YES cluster
    u = [{**x, "y": 1.0 if i < 40 else 0.5 if i < 80 else 0.0} for i, x in enumerate(hi)]
    g = G.inverted_tail_gate(u)
    assert g["pi_hat"] == pytest.approx((40 + 20) / 400) and g["yes_event_clusters"] == 40


def test_neg_risk_placebo_draw_is_mutually_exclusive():
    base = {"event": "E1", "neg_risk": True, "m": 0.4, "rate": 0.0, "y": 0.0, "hold_d": 7.0, "ew": "E1|w", "theme": "t"}
    units = [{**base, "market_id": "a"}, {**base, "market_id": "b"}, {**base, "market_id": "c"}]
    ps = G.placebo_structure(units)
    assert ps["scale"][0] < 1.0  # 3 x (0.4 + a spread) > 1: intervals are scaled down to stay disjoint
    rng = np.random.default_rng(3)
    for _ in range(2000):
        u = rng.random(1)[ps["e"]]
        y = (u >= ps["offset"]) & (u < ps["offset"] + ps["q"] * ps["scale"])
        assert y.sum() <= 1
    # non-neg-risk markets of one event are comonotone: nested from 0
    base2 = {**base, "neg_risk": False}
    ps2 = G.placebo_structure([{**base2, "market_id": "a", "m": 0.05}, {**base2, "market_id": "b", "m": 0.09}])
    assert list(ps2["offset"]) == [0.0, 0.0] and list(ps2["scale"]) == [1.0, 1.0]


def test_breakeven_placebo_is_calibrated_by_construction():
    units, _ = g_units()
    pl = G.breakeven_g1(units)
    assert pl["n_draws"] == 200 and pl["seed"] == 7174 and pl["advance_rate"] <= 0.03


def test_g1_full_evaluation_advances_on_a_broad_effect_and_holm_decides():
    units, unres = g_units()
    res = G.evaluate_g1(units, unres, h_geo=0.012, cumulative_count=1121)
    assert res["unit_level_pass"], (res["failed_checks"], res["unverified_checks"])
    holm = {"tests": st.holm_table({"S1": 1.0, "G1": res["p"], "X1": 1.0}, 0.01)}
    res = G.decide(res, holm)
    assert res["advance"] and res["batch_holm_reject"] and "Stage P-G" in res["verdict"]
    # same unit-level pass but a Holm that does not reject (p just above alpha / 3) -> not advanced
    res2 = G.decide({**res, "advance": None}, {"tests": st.holm_table({"S1": 1.0, "G1": 0.004, "X1": 1.0}, 0.01)})
    assert not res2["advance"] and "batch_holm" in res2["verdict"]


def test_g1_robustness_end_date_cost_spread_subset_and_worst_case():
    early = set(range(0, 400, 5))  # every YES unit resolved early (closed_time < end - 2 d)
    units, unres = g_units(early=early)
    rob = G.robustness(units, unres, 0.012)
    assert rob["vii_drop_closed_before_end_minus_2d"]["n_dropped"] == 80 and rob["vii_drop_closed_before_end_minus_2d"]["ok"] is False
    units, unres = g_units()
    assert G.robustness(units, unres, None)["ix_measured_spread"]["ok"] is None  # unavailable -> unverified
    assert G.robustness(units, unres, 0.20)["ix_measured_spread"]["ok"] is False  # a = m + 0.20: net < 0
    assert G.robustness(units, unres, 0.012)["ix_measured_spread"]["ok"] is True
    # censored units at Y = 0 flip the sign when there are enough of them
    cens = [{**units[0], "y": None, "status": "censored", "market_id": f"c{i}"} for i in range(2500)]
    assert G.robustness(units, cens, 0.012)["v_censored_y0"]["ok"] is False
    assert G.robustness(units, [], 0.012)["i_cost_0.75c"]["ok"] is True
    # the tag-and-topic subset: question without a geopolitical word is tag-only
    mixed, _ = g_units(question="Will event {i} happen?")
    assert not any(u["tag_topic"] for u in mixed)
    assert G.robustness(mixed, [], 0.012)["x_tag_and_topic_subset"]["ok"] is False


def test_g1_broad_effect_required_five_events_cannot_carry_it():
    # 12 winning events, each a theme and event cluster of their own: removing the top 5 leaves a null
    units, unres = g_units(yes=range(0, 120, 10))
    t = G.g1_test(units)
    rob = G.robustness(units, unres, 0.012)
    assert t["yes_event_clusters"] == 12
    assert rob["ii_without_top5"]["ok"] is False


# ---- stats, Holm, k2 -------------------------------------------------------------------------------------------------------------------


def test_ways_test_rules():
    v = np.r_[np.full(60, 1.0), np.full(60, -0.5)] + np.random.default_rng(1).normal(0, 0.1, 120)
    ways = {"a": np.arange(120) % 40, "b": np.arange(120) % 20}
    t = st.ways_test(v, ways, sign=1, min_clusters={"a": 30, "b": 15})
    assert t["testable"] and t["G"] == {"a": 40, "b": 20}
    assert not st.ways_test(v, {"a": np.arange(120) % 25, "b": ways["b"]}, sign=1, min_clusters={"a": 30, "b": 15})["testable"]  # event way < 30
    assert not st.ways_test(v, {"a": ways["a"], "b": np.arange(120) % 12}, sign=1, min_clusters={"a": 30, "b": 15})["testable"]  # small-G < 15
    assert not st.ways_test(v[:99], {k: x[:99] for k, x in ways.items()}, sign=1, min_clusters={"a": 30, "b": 15})["testable"]  # < 100 units
    neg = st.ways_test(-np.abs(v) - 1, ways, sign=-1, min_clusters={"a": 30, "b": 15})
    assert neg["p"] < 1e-3  # (Webb wild-bootstrap floor 1e-4 at 15 <= G < 30) sign -1 tests mean < 0


def test_batch_holm_and_k2(tmp_path):
    (tmp_path / "results_S1.json").write_text(json.dumps({"p": 1.0, "advance": False}))
    lab = st.batch_holm_label("G1", 0.003, tmp_path)
    assert lab["tests"]["G1"]["reject"] and lab["not_final_as_p1"] == ["X1"] and lab["k1"] == 3 and not lab["final"]
    assert not st.batch_holm_label("G1", 0.004, tmp_path)["tests"]["G1"]["reject"]  # needs p <= alpha / 3
    assert st.stage2_k(tmp_path)["k2"] is None
    (tmp_path / "results_X1.json").write_text(json.dumps({"p": 0.001, "advance": True}))
    assert st.stage2_k(tmp_path)["k2"] == 1
    (tmp_path / "results_X1.json").unlink()
    (tmp_path / "results_X1.json").write_text(json.dumps({"p": 0.5, "advance": False}))
    assert st.stage2_k(tmp_path)["k2"] == 0
    assert st.by_label(1e-9, 1124)["by_significant"] and not st.by_label(0.01, 1124)["by_significant"]


# ---- X fixtures ------------------------------------------------------------------------------------------------------------------------

BASE = 1_767_225_600  # 2026-01-01T00:00Z (before the rebate date)


def x_pair(i, *, steps=None, follow=True, seed=0, cat="Politics", base=BASE, every=120, days=2):
    rng = np.random.default_rng(seed * 1000 + i)
    ws = base + i * 86400
    we = ws + days * 86400
    if steps is None:
        steps = [(ws + 3 * 3600 + 6 * 3600 * j, 0.02 if j % 2 == 0 else -0.02) for j in range(8)]

    def level(t):
        return 0.50 + sum(d for s, d in steps if s <= t)

    tm = np.arange(ws + 60, we + 1, 60.0)
    mid = np.array([level(t) for t in tm])
    kc = np.column_stack([tm, mid - 0.01, mid + 0.01, mid, np.ones_like(tm)])
    pt = np.arange(ws, we + 1, 600.0)
    ps = np.column_stack([pt, [level(t - 1800) if follow else 0.50 for t in pt]])
    ts = ws + 7 + every * np.arange(int(days * 86400 / every)) + rng.integers(0, 30, int(days * 86400 / every))
    side = rng.choice([1.0, -1.0], len(ts))
    pm = np.array([level(t - 1800) if follow else 0.50 for t in ts])
    px = pm + side * 0.01 + rng.uniform(-0.003, 0.003, len(ts))
    pr = np.column_stack([ts, side, px, rng.integers(5, 50, len(ts)).astype(float)])
    return {"key": f"P{i}", "event": f"E{i}", "cat": cat, "win": (float(ws), float(we)), "kc": kc, "ps": ps, "prints": pr}


def x_set(n=40, **kw):
    xs = X.XSet()
    for i in range(n):
        p = x_pair(i, **kw)
        xs.add_pair(p["key"], p["event"], p["cat"], p["win"], p["kc"], p["ps"], p["prints"])
    return xs.finish()


@pytest.fixture(scope="module")
def xs_follow():
    return x_set()


def test_x_vectors_match_census(xs_follow):
    # one pair with a spike (up then down 20 minutes later) so that prints fall in both states
    ws = BASE
    p = x_pair(0, steps=[(ws + 3 * 3600, 0.02), (ws + 3 * 3600 + 1200, -0.02), (ws + 9 * 3600, -0.02)])
    xs = X.XSet()
    xs.add_pair("P0", "E0", "Politics", p["win"], p["kc"], p["ps"], p["prints"])
    xs.finish()
    up, dn = xs.skip_states(X.LAG_S, X.SKIP_LEN_S)
    cl = X.classify(xs, up, dn)
    km = xv.KalshiMid(p["kc"])
    u, d = xv.move_events(km)
    ref = xv.classify_prints([(float(t), int(s)) for t, s in zip(p["prints"][:, 0], p["prints"][:, 1], strict=True)], u, d, km, p["ps"][:, 0], p["ps"][:, 1])
    assert ref["excluded_both_states"] > 0
    assert int(cl["S"].sum()) == ref["S"] and int(cl["Sp"].sum()) == ref["Sp"] and int(cl["N"].sum()) == ref["N"]
    assert int(cl["excluded_both"].sum()) == ref["excluded_both_states"] and int(cl["excluded_unusable"].sum()) == ref["excluded_unusable"]
    m = xs.marks(3600.0)
    assert int((cl["S"] & np.isfinite(m)).sum()) == ref["S_mark_available"]


def test_mark_uses_only_points_stamped_before_u_minus_600():
    ps_ts = np.array([1000.0, 2000.0, 3399.0, 3401.0])
    ps_px = np.array([0.4, 0.5, 0.6, 0.99])
    u = np.array([4000.0])  # u - 600 = 3400: the point at 3401 is NOT usable, 3399 is
    assert X.mark_at(ps_ts, ps_px, u)[0] == 0.6
    assert np.isnan(X.mark_at(ps_ts, ps_px, np.array([8000.0]))[0])  # nothing in [u - 3600, u - 600]


def test_side_mapping_markout_and_rebate():
    xs = x_set(2)
    side, px = xs.cols["side"], xs.cols["px"]
    mo = X.markout(xs, np.full(len(px), 0.5))
    assert np.allclose(mo, side * (px - 0.5))  # ask-side p - M, bid-side M - p
    assert float(xs.cols["reb"].max()) == 0.0  # Jan-Feb 2026: before the 2026-03-30 rebate date
    late = X.XSet()
    p = x_pair(0, base=1_775_000_000, cat="Politics")  # April 2026
    late.add_pair("P0", "E0", "Politics", p["win"], p["kc"], p["ps"], p["prints"])
    late.finish()
    pp = late.cols["px"]
    assert np.allclose(late.cols["reb"], 0.25 * 0.04 * pp * (1 - pp))
    assert X.rebate_rate("politics") == pytest.approx(0.01)
    assert X.rebate_rate("zzz-unmatched") == pytest.approx(max(economics_rate for economics_rate in (0.2 * 0.07, 0.15 * 0.05, 0.25 * 0.05, 0.25 * 0.04)))


def test_x1_known_answer_when_polymarket_follows_kalshi(xs_follow):
    c = X.core(xs_follow)
    t = X.x1_test(c["S_units"])
    assert t["testable"] and t["mean"] < -0.005 and t["p"] < 1e-6
    # S marks out negative, S' positive, kept fills (N) positive: the spread the maker earns
    sp = c["cl"]["Sp"] & c["avail"]
    assert c["mo"][sp].mean() > 0.02
    assert X.route_gate(xs_follow, c)["ok"] is True
    ld = X.lead_decomposition(xs_follow, c)
    assert ld["sum"] == pytest.approx(t["mean"], abs=1e-9)  # the decomposition is exact


def test_x1_full_evaluation_advances_and_credits_the_skew(xs_follow):
    res = X.evaluate_x1(xs_follow, None, cumulative_count=1121)
    assert res["advance"], (res["failed_checks"], res["unverified_checks"])
    assert res["placebo_time_shift"]["n_draws"] == 200 and res["placebo_time_shift"]["seed"] == 7175 and res["placebo_time_shift"]["calibrated"]
    assert res["wrong_side"]["credited"] is True
    assert res["robustness"]["viii_latency_300s"]["ok"] and res["robustness"]["i_alternative_mark"]["ok"]


def test_x1_null_fixture_is_not_detected():
    xs = x_set(40, follow=False)  # Polymarket does not follow Kalshi: skipped fills still earn the spread
    res = X.evaluate_x1(xs, None, cumulative_count=1121, with_placebo=False)
    assert res["testable"] and not res["advance"] and res["effect"] > 0 and res["p"] > 0.5


def test_route_gate_failure_blocks_advance_with_the_declared_verdict():
    xs = x_set(40)
    c = X.core(xs)
    kept = (c["cl"]["N"] | c["cl"]["Sp"]) & c["avail"]
    bad = c["mo"].copy()
    bad[kept] = -0.05
    g = X.route_gate(xs, {**c, "mo": bad})
    assert g["ok"] is False and "no route" in g["label"]


def test_wrong_side_attribution_fails_when_both_sides_are_adverse():
    a = st.attribution(-0.01, [-0.01, -0.012], -1, ("skew credited", "pause, not a skew"), "wrong-side")
    assert a["credited"] is False and "pause" in a["label"]
    b = st.attribution(-0.01, [0.03], -1, ("skew credited", "pause, not a skew"), "wrong-side")
    assert b["credited"] is True
    assert st.attribution(-0.01, [], -1, ("a", "b"), "x")["credited"] is None  # unverified never credits


def test_time_shift_offsets_stay_inside_6h_and_w_minus_6h():
    xs = X.XSet()
    w = 30 * 3600.0
    t0 = BASE
    p = x_pair(0)
    xs.add_pair("P", "E", "Politics", (t0, t0 + w), p["kc"], p["ps"], p["prints"])
    xs.finish()
    xs.parts[0]["up"] = np.array([t0 + 1000.0])
    xs.parts[0]["down"] = np.array([])
    rng = np.random.default_rng(1)
    for _ in range(300):
        (u, _d) = X.shifted_taus(xs, rng)[0]
        off = (u[0] - (t0 + 1000.0)) % w
        assert 6 * 3600 - 1e-6 <= off <= w - 6 * 3600 + 1e-6


def test_time_shift_placebo_advances_about_one_percent_or_less_on_a_null_link():
    xs = x_set(40, follow=False, seed=3)
    pl = X.time_shift_placebo(xs, draws=60)
    assert pl["advance_rate"] <= 0.05  # the shift destroys the timing link; 200 draws are used by the screen


def test_no_wallet_or_outcome_column_is_read_by_the_x_analysis():
    src = Path(X.__file__).read_text()
    assert "proxywallet" not in src.lower() and "wallet" not in src.lower().replace("no wallet", "")
    assert "outcomes_guarded" not in src and "outcome_prices" not in src


# ---- declaration, KIND_RULES, runner ----------------------------------------------------------------------------------------------------


def test_kind_rules_have_the_cb7_kinds_and_count_zero():
    for k in ("cb7_test", "cb7_replication", "cb7_descriptive"):
        assert battery2.KIND_RULES[k][0] == battery2.EXCLUDE
    assert battery2.count_line({"kind": "cb7_test", "n_tests": 1, "p": 0.5})[1] == 0
    assert battery2.count_line({"kind": "cb7_replication", "n_tests": 1})[1] == 0
    assert battery2.count_line({"kind": "ml_explain", "source": "creative_batch_7:G", "n_tests": 1})[1] == 1
    p = Path(__file__).resolve().parents[2] / "backend" / "astrolabe" / "research_lab"
    assert p.exists()
    from astrolabe.research_lab import provenance

    if provenance.TRIALS_PATH.exists():
        assert battery2.cumulative_count(provenance.TRIALS_PATH)["total"] >= 0  # the real trials log still parses with the new kinds


def test_declaration_is_stable_and_binds_constants_and_functions(monkeypatch):
    a = D.declaration_sha256()
    assert a == D.declaration_sha256() and len(a) == 64
    monkeypatch.setattr(G, "FLOOR_NET", 0.02)
    assert D.declaration_sha256() != a
    monkeypatch.undo()
    monkeypatch.setattr(st, "ALPHA1", 0.02)
    assert D.declaration_sha256() != a
    monkeypatch.undo()
    blob = D.declaration_blob()
    assert {"S1", "G1", "X1"} == set(blob["hypotheses"]) and blob["counting"]["k1"] == 3
    srcs = blob["function_sources_sha256"]
    assert "cb7_g_analysis.inverted_tail_gate" in srcs and "cb7_x_analysis.time_shift_placebo" in srcs and "cb2_weather.small_g_pvalue" in srcs
    assert blob["constants"]["cb7_astats"]["SEEDS"]["X_time_shift"] == 7175 and blob["constants"]["cb7_astats"]["N_BOOT"] == 2000


def test_t7_x_list_rule():
    assert D.t7_x_list("2026-10-31T10:00:00Z") == "2026-11-03T06:00:00Z"  # the floor
    assert D.t7_x_list("2026-11-05T10:00:00Z") == "2026-11-06T10:00:00Z"  # freeze + 24 h


def _census_doc(**over):
    doc = {"version": "cb7-census-v1", "rules_sha256": D.rules_sha256(), "declaration": cc.census_declaration(), "seals": {},
           "S": {"status": "ok", "gate_GS": {"GS": False, "units": {"value": 787, "need": 3000, "met": False}}, "s1_mde_per_marker_cents": 7.0},
           "G": {"status": "ok", "gate_GG": {"GG": False}}, "X": {"status": "ok", "gate_GX": {"GX": False}}}
    doc.update(over)
    return doc


def _frozen(tmp_path, *, not_before="2020-01-02T00:00:00Z", census=None, mutate=None):
    cb7 = tmp_path / "creative_batch7"
    cb7.mkdir(exist_ok=True)
    cj = cb7 / "census.json"
    cj.write_text(json.dumps(census or _census_doc()))
    spec = D.spec_payload(census_json=cj, freeze_utc="2020-01-01T00:00:00Z", screen_not_before_utc=not_before)
    if mutate:
        mutate(spec)
    sp = tmp_path / "cb7_v1.json"
    sp.write_text(json.dumps(spec))
    (tmp_path / "trials.jsonl").write_text("")
    return cb7, sp


def _screen(fam, tmp_path, sp, cb7, extra=()):
    return RUN.main(["screen", "--family", fam, "--freeze-spec", str(sp), "--out-root", str(cb7), "--root", str(tmp_path / "history"), "--seals-dir", str(tmp_path / "seals"),
                     "--trials-path", str(tmp_path / "trials.jsonl"), "--cv-root", str(tmp_path / "cv"), "--allow-uncommitted-rules", *extra])


def test_screen_refuses_without_the_freeze_file(tmp_path, capsys):
    cb7, _sp = _frozen(tmp_path)
    assert _screen("S", tmp_path, tmp_path / "missing.json", cb7) == 2
    assert "not found" in _out(capsys)["refused"]
    assert not (cb7 / "results_S1.json").exists()


def test_screen_refuses_on_any_pin_mismatch(tmp_path, capsys):
    for field, mut in (("declaration_sha256", lambda s: s.update(declaration_sha256="0" * 64)), ("rules_sha256", lambda s: s.update(rules_sha256="1" * 64)),
                       ("source", lambda s: s["sources"].update({"scripts/run_cb7.py": "2" * 64})), ("version", lambda s: s.update(version="x"))):
        sub = tmp_path / field
        sub.mkdir()
        cb7, sp = _frozen(sub, mutate=mut)
        assert _screen("S", sub, sp, cb7) == 2, field
        assert "does not carry" in _out(capsys)["refused"]
        assert not (cb7 / "results_S1.json").exists()


def test_screen_refuses_before_its_declared_time_and_opens_no_outcome(tmp_path, capsys):
    cb7, sp = _frozen(tmp_path, not_before="2099-01-01T00:00:00Z")
    for fam in ("S", "G", "X"):
        assert _screen(fam, tmp_path, sp, cb7) == 2
        assert "declared time" in _out(capsys)["refused"]
    assert not list(cb7.glob("results_*.json")) and (tmp_path / "trials.jsonl").read_text() == ""


def test_outcome_gate_never_calls_the_reader_before_the_declared_time():
    calls = []
    gate = st.OutcomeGate(2_000.0, wall_clock=lambda: 1_999.0)
    with pytest.raises(cm.Refused):
        gate.read(lambda: calls.append(1))
    assert calls == [] and gate.reads == 0
    ok = st.OutcomeGate(2_000.0, wall_clock=lambda: 2_000.0)
    assert ok.read(lambda: calls.append(1) or "x") == "x" and ok.reads == 1
    src = Path(G.__file__).read_text()
    assert src.count("cm.OUTCOME_FILE") == 1 and "gate.read(_read_outcomes)" in src  # the only door to the guarded file


def test_screen_refuses_census_sha_and_declaration_mismatch(tmp_path, capsys):
    cb7, sp = _frozen(tmp_path)
    (cb7 / "census.json").write_text(json.dumps(_census_doc(extra="changed")))
    assert _screen("S", tmp_path, sp, cb7) == 2 and "census.json sha256" in _out(capsys)["refused"]
    sub = tmp_path / "decl"
    sub.mkdir()
    cb7b, spb = _frozen(sub)
    bad = _census_doc()
    bad["declaration"] = {**bad["declaration"], "constants_sha256": "f" * 64}
    (cb7b / "census.json").write_text(json.dumps(bad))
    with pytest.raises(ValueError):  # the freeze refuses to pin a census whose declaration hashes differ from this code
        D.spec_payload(census_json=cb7b / "census.json", freeze_utc="2020-01-01T00:00:00Z", screen_not_before_utc="2020-01-02T00:00:00Z")
    _ = spb


def test_screen_rejects_unknown_or_multiple_families(tmp_path, capsys):
    cb7, sp = _frozen(tmp_path)
    for fam in ("S,G", "Z", ""):
        assert _screen(fam, tmp_path, sp, cb7) == 2
        assert "exactly one family" in _out(capsys)["refused"]


def test_screen_s_writes_the_counted_p1_line_without_q0156(tmp_path, capsys):
    cb7, sp = _frozen(tmp_path)
    before = battery2.cumulative_count(tmp_path / "trials.jsonl")["total"]
    assert _screen("S", tmp_path, sp, cb7) == 0
    out = _out(capsys)
    assert out["test"] == "S1" and out["p"] == 1.0 and out["testable"] is False and out["advance"] is False
    doc = json.loads((cb7 / "results_S1.json").read_text())
    assert doc["verdict"] == "not testable (GS failed in the census)" and "q0156" in doc["dependency_removed"] and doc["s2"].startswith("not run")
    assert doc["labels_stage1"]["batch_holm"]["tests"]["S1"]["p"] == 1.0
    assert (tmp_path / "seals" / "cb7_s1_stage1.json").read_bytes() == (cb7 / "results_S1.json").read_bytes()
    lines = [json.loads(x) for x in (tmp_path / "trials.jsonl").read_text().splitlines()]
    kinds = [(x["kind"], x.get("source")) for x in lines]
    assert ("cb7_test", None) in kinds and ("cb7_descriptive", None) in kinds and ("ml_explain", "creative_batch_7:S") in kinds
    t = next(x for x in lines if x["kind"] == "cb7_test")
    assert t["p"] == 1.0 and t["testable"] is False and t["n_tests"] == 0
    assert battery2.cumulative_count(tmp_path / "trials.jsonl")["total"] == before + 1  # counted exactly once
    assert _screen("S", tmp_path, sp, cb7) == 2  # write-once: never overwritten
    assert len((tmp_path / "trials.jsonl").read_text().splitlines()) == len(lines)


def test_screen_s_refuses_if_gs_were_true(tmp_path, capsys):
    c = _census_doc()
    c["S"]["gate_GS"]["GS"] = True
    cb7, sp = _frozen(tmp_path, census=c)
    assert _screen("S", tmp_path, sp, cb7) == 2 and "not implemented" in _out(capsys)["refused"]


def test_screen_g_and_x_gate_failures_are_counted_not_testable(tmp_path, capsys):
    cb7, sp = _frozen(tmp_path)
    assert _screen("G", tmp_path, sp, cb7) == 0
    assert _out(capsys)["verdict"] == "not testable (GG failed in the census)"
    assert _screen("X", tmp_path, sp, cb7) == 0
    assert _out(capsys)["verdict"] == "not testable (GX failed in the census)"
    lines = [json.loads(x) for x in (tmp_path / "trials.jsonl").read_text().splitlines()]
    assert sorted(x["source"] for x in lines if x["kind"] == "ml_explain") == ["creative_batch_7:G", "creative_batch_7:X"]
    lab = json.loads((cb7 / "results_X1.json").read_text())["labels_stage1"]["batch_holm"]
    assert lab["tests"]["G1"]["p"] == 1.0 and lab["not_final_as_p1"] == ["S1"]


def test_screen_deadline_state_is_not_run_p1(tmp_path, capsys):
    c = _census_doc()
    c["G"] = {"status": cm.NOT_RUN_TOKEN}
    cb7, sp = _frozen(tmp_path, census=c)
    assert _screen("G", tmp_path, sp, cb7) == 0
    assert _out(capsys)["verdict"] == "not run (deadline)"


def test_write_spec_dry_run_and_never_overwrites(tmp_path, capsys):
    cb7, _ = _frozen(tmp_path)
    args = ["write-spec", "--census-json", str(cb7 / "census.json"), "--freeze-utc", "2026-10-31T10:00:00Z", "--screen-not-before-utc", "2026-10-31T12:00:00Z",
            "--path", str(tmp_path / "out_spec.json")]
    assert RUN.main([*args, "--dry-run"]) == 0
    out = _out(capsys)
    assert out["dry_run"] and out["payload"]["dates"]["T7_X_list"] == "2026-11-03T06:00:00Z" and out["payload"]["dates"]["T7_S_rep_start"] == "not applicable"
    assert out["payload"]["queue"]["do_not_promote"] == ["q0151", "q0152", "q0156"] and not (tmp_path / "out_spec.json").exists()
    assert RUN.main(["write-spec", "--census-json", str(cb7 / "census.json"), "--freeze-utc", "2026-10-31T10:00:00Z", "--screen-not-before-utc", "2026-10-31T09:00:00Z",
                     "--path", str(tmp_path / "out_spec.json"), "--dry-run"]) == 2  # a screen time before the freeze is refused


# ---- G end to end on sealed synthetic tables ---------------------------------------------------------------------------------------------


def _gz_csv(path: Path, header: list[str], rows: list[dict]) -> None:
    with gzip.open(path, "wt", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for r in rows:
            w.writerow([r.get(c, "") for c in header])


def _seal(root: Path, seals: Path, run: str, files: dict[str, tuple[list[str], list[dict]]] | None, trials: Path) -> None:
    d = root / run
    d.mkdir(parents=True)
    for name, (head, rows) in (files or {}).items():
        _gz_csv(d / name, head, rows)
    (d / "manifest.json").write_text(json.dumps({"run_id": run, "complete": True}))
    h5_seal.seal_run(d, trials_path=trials, declaration_base={"d": run})
    h5_seal.write_committed_copy(d, seals)


@pytest.fixture()
def sealed_g(tmp_path):
    root, seals = tmp_path / "history", tmp_path / "seals"
    rows, prices, outcomes = g_tables(n_ev=400, yes=range(0, 400, 5))
    sample_cols = list(rows[0])
    _seal(root, seals, "h8_text", None, tmp_path / "seal_trials.jsonl")
    _seal(root, seals, "h8_tail", None, tmp_path / "seal_trials.jsonl")
    _seal(root, seals, "h8_geo", {"sample.csv.gz": (sample_cols, rows), "origin_prices.csv.gz": (list(prices[0]), prices), "drops.csv.gz": (["market_id", "block", "reason"], []),
                                  cm.OUTCOME_FILE: (["market_id", "outcome_prices", "uma_status"], [{"market_id": k, "outcome_prices": v, "uma_status": "resolved"} for k, v in outcomes.items()])},
          tmp_path / "seal_trials.jsonl")
    return tmp_path


def test_screen_g_end_to_end_reads_outcomes_only_after_the_declared_time(sealed_g, capsys):
    tmp_path = sealed_g
    geo_listing = json.loads((tmp_path / "history" / "h8_geo" / "SEAL.json").read_text())["listing_sha256"]
    census = _census_doc(G={"status": "ok", "gate_GG": {"GG": True}, "h_geo": {"h_geo_binding": 0.012}, "seal_listing_sha256": geo_listing})
    # before the declared time: refusal, and the guarded file is not touched (access log stays empty)
    early_dir = tmp_path / "early"
    early_dir.mkdir()
    cb7e, spe = _frozen(early_dir, not_before="2099-01-01T00:00:00Z", census=census)
    assert RUN.main(["screen", "--family", "G", "--freeze-spec", str(spe), "--out-root", str(cb7e), "--root", str(tmp_path / "history"), "--seals-dir", str(tmp_path / "seals"),
                     "--trials-path", str(early_dir / "trials.jsonl"), "--allow-uncommitted-rules"]) == 2
    _out(capsys)
    assert (tmp_path / "history" / "h8_geo" / "ACCESS_LOG.jsonl").read_text() == ""
    cb7, sp = _frozen(tmp_path, census=census)
    assert _screen("G", tmp_path, sp, cb7) == 75  # waits for the S1 and X1 Stage-1 files (final batch Holm); no sealed file opened
    assert "run those screens first" in _out(capsys)["tempfail"]
    assert (tmp_path / "history" / "h8_geo" / "ACCESS_LOG.jsonl").read_text() == ""
    (cb7 / "results_S1.json").write_text(json.dumps({"p": 1.0, "advance": False}))
    (cb7 / "results_X1.json").write_text(json.dumps({"p": 0.5, "advance": False}))
    t0 = time.time()
    assert _screen("G", tmp_path, sp, cb7) == 0
    out = _out(capsys)
    assert out["test"] == "G1" and out["testable"] is True and out["p"] < 1e-6
    doc = json.loads((cb7 / "results_G1.json").read_text())
    assert doc["inputs"]["outcome_reads"] == 1 and doc["inputs"]["n_resolved"] == 400 and doc["unit_level_pass"] is True
    assert doc["advance"] is True and doc["batch_holm_reject"] is True and doc["labels_stage1"]["batch_holm"]["final"] is True
    access = (tmp_path / "history" / "h8_geo" / "ACCESS_LOG.jsonl").read_text()
    assert cm.OUTCOME_FILE in access and "q0149_cb7_screen_G" in access
    assert time.time() - t0 < 300
    lines = [json.loads(x) for x in (tmp_path / "trials.jsonl").read_text().splitlines()]
    assert sum(1 for x in lines if x["kind"] == "ml_explain") == 1 and any(x.get("evidence_role") == "placebo" and x["n_tests"] == 0 for x in lines)
    assert battery2.cumulative_count(tmp_path / "trials.jsonl")["total"] == 1


def test_screen_refuses_a_refused_root(tmp_path, capsys):
    cb7, sp = _frozen(tmp_path)
    bad = tmp_path / "cb6_extract" / "x"
    bad.mkdir(parents=True)
    assert RUN.main(["screen", "--family", "S", "--freeze-spec", str(sp), "--out-root", str(bad), "--allow-uncommitted-rules"]) == 2
    assert "refused" in _out(capsys)["refused"]
    _ = cb7


def test_s_module_does_not_implement_the_slope():
    src = Path(S.__file__).read_text()
    assert "outcomes_guarded" not in src and "def s1_beta" not in src
