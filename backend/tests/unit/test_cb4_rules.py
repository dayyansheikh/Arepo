# ruff: noqa: E501
"""CB4 route rules (CH46 / CH50) on synthetic data."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import cb4_declaration as D
from astrolabe.research_lab import cb4_rules as R

H, DAY = 3600.0, 86400.0
T0 = 1_790_000_000.0  # arbitrary epoch


def _iso(ts):
    return D.iso(ts)


def cw_row(cap_id, cap_start, market, *, e, acc="1", closed="0", uma="", ext="1", created=None, bid="0.40", ask="0.44", cat="politics", event="E1", recv_off=60):
    return {"capture_id": cap_id, "capture_start_utc": _iso(cap_start), "received_utc": _iso(cap_start + recv_off), "market_id": market, "condition_id": "c" + market, "event_id": event,
            "clob_token_id_0": "t0", "clob_token_id_1": "t1", "best_bid": bid, "best_ask": ask, "spread": "0.04", "last_trade_price": "0.4", "closed": closed, "active": "1",
            "accepting_orders": acc, "end_date": _iso(e), "created_at": _iso(created if created is not None else e - 10 * DAY), "uma_resolution_statuses": uma, "volume_num": "1",
            "fee_schedule": "", "fee_category": cat, "neg_risk_market_id": "", "series_slugs": "", "sweep_best_bid": "", "sweep_best_ask": "", "sweep_bid_size_1": "50", "sweep_ask_size_1": "40",
            "ext_present": ext}


def parsed(rows):
    return R.parse_closewin(pd.DataFrame(rows))


# ---- C2 population fixed at tau0 -----------------------------------------------------------------------------------------------


def test_c2_selected_from_capture_alone():
    c0 = T0
    rows = [cw_row("c0", c0, "m1", e=c0 + 3600 * 1.5)]
    later = [cw_row("c1", c0 + 2 * H, "m1", e=c0 + 3600 * 1.5, acc="0", uma='["proposed"]')]  # later flip + UMA proposal
    u1, _ = R.c2_units_at_tau0(parsed(rows))
    u2, _ = R.c2_units_at_tau0(parsed(rows + later))
    assert set(u1["market_id"]) == {"m1"}
    assert u1[["market_id", "token", "q", "tau0", "e"]].equals(u2[["market_id", "token", "q", "tau0", "e"]])
    assert sorted(u1["token"]) == [0, 1]
    yes, no = u1[u1["token"] == 0].iloc[0], u1[u1["token"] == 1].iloc[0]
    assert yes["q"] == pytest.approx(0.40) and no["q"] == pytest.approx(1 - 0.44)
    assert yes["tau0"] == pytest.approx(c0 + 60 + 600)


@pytest.mark.parametrize("kw,key", [
    ({"acc": "0"}, "not_accepting"), ({"closed": "1"}, "closed"), ({"uma": '["proposed"]'}, "uma_not_clear"), ({"ext": "0"}, "uma_unknown"),
    ({"e_off": 3 * H}, "end_window"), ({"created_off": 5 * H}, "life"), ({"cat": "weather"}, "weather")])
def test_c2_exclusions_counted(kw, key):
    kw = dict(kw)
    e = T0 + (kw.pop("e_off", 1.5 * H))
    created = e - kw.pop("created_off") if "created_off" in kw else None
    u, rep = R.c2_units_at_tau0(parsed([cw_row("c0", T0, "m1", e=e, created=created, **kw)]))
    assert len(u) == 0 and rep[key] >= 1


def test_c2_no_bid_token_and_first_capture_only():
    rows = [cw_row("c0", T0, "m1", e=T0 + 1.9 * H, bid="", ask="0.5"), cw_row("c1", T0 + 2 * H, "m1", e=T0 + 3.5 * H)]
    u, _ = R.c2_units_at_tau0(parsed(rows))
    assert sorted(u["token"]) == [1]  # YES has no recorded bid at c0 and c0 is the first qualifying capture
    assert set(u["capture_id"]) == {"c0"}


# ---- strata ----------------------------------------------------------------------------------------------------------------------


def _pair(a_kw, b_row_kw=None, *, gap=2 * H, e_off=1.0 * H, b_present=True, dep=False, uma_b="", ext_b="1"):
    a = parsed([cw_row("c0", T0, "m1", e=T0 + e_off, **a_kw)])
    rows_b = [cw_row("c1", T0 + gap, "m1", e=T0 + e_off, acc="0", uma=uma_b, ext=ext_b, **(b_row_kw or {}))] if b_present else [cw_row("c1", T0 + gap, "mX", e=T0 + 99 * DAY)]
    b = parsed(rows_b)
    st, rep = R.assign_strata([a, b], {"c1": {"m1"} if dep else set()})
    return st, rep


def test_strata_S_E_L_P_N_unknown():
    s, _ = _pair({})
    assert s.set_index("market_id").loc["m1", "stratum"] == "S"
    e, _ = _pair({}, e_off=2.5 * H)  # e after start(c_k+1) = T0 + 2h
    assert e.set_index("market_id").loc["m1", "stratum"] == "E"
    late, _ = _pair({}, e_off=-3 * H)  # e <= start_k - 2h
    assert late.set_index("market_id").loc["m1", "stratum"] == "L"
    p, _ = _pair({}, uma_b='["proposed"]')
    assert p.set_index("market_id").loc["m1", "stratum"] == "P"
    n, _ = _pair({}, b_present=False, dep=True)
    assert n.set_index("market_id").loc["m1", "stratum"] == "N"
    u, _ = _pair({}, ext_b="0")
    assert u.set_index("market_id").loc["m1", "stratum"] == "unknown"


def test_strata_gap_outside_filter_and_e_from_earlier_capture():
    st, rep = _pair({}, gap=4 * H)
    assert len(st[st["stratum"] != "U"]) == 0 and rep["pairs_gap_excluded"] == 1
    a = parsed([cw_row("c0", T0, "m1", e=T0 + 1.0 * H)])
    b = parsed([cw_row("c1", T0 + 2 * H, "m1", e=T0 + 50 * DAY, acc="0")])  # later capture shows a different end_date
    st, _ = R.assign_strata([a, b], {})
    assert st.iloc[0]["e"] == pytest.approx(T0 + H)


def test_strata_U_and_reopening_counted():
    caps = [parsed([cw_row(f"c{i}", T0 + i * 2 * H, "m1", e=T0 + 1 * H, acc="1")]) for i in range(5)]
    st, _ = R.assign_strata(caps, {})
    assert st.iloc[0]["stratum"] == "U"
    a = parsed([cw_row("c0", T0, "m1", e=T0 + H)])
    b = parsed([cw_row("c1", T0 + 2 * H, "m1", e=T0 + H, acc="0")])
    c = parsed([cw_row("c2", T0 + 4 * H, "m1", e=T0 + H, acc="1")])
    d = parsed([cw_row("c3", T0 + 6 * H, "m1", e=T0 + H, acc="1")])
    st, rep = R.assign_strata([a, b, c, d], {})
    assert st.iloc[0]["stratum"] == "S" and rep["reopenings"] >= 1


# ---- prints, C1, C2 ----------------------------------------------------------------------------------------------------------------


def trades_df(rows):
    return pd.DataFrame(rows, columns=["ts", "side", "size", "price", "outcome_index"]).assign(wallet_hash="w", trade_key=lambda d: d.index.astype(str))


def mk_market(e, pf, pb, *, tok=0, n=2, truncated=False, oldest=None):
    rows = [(e - 1 * H - i, "SELL", 5.0, pf + 0.001 * i, tok) for i in range(n)] + [(e - 25 * H - i, "SELL", 5.0, pb - 0.001 * i, tok) for i in range(n)]
    return R.Trades(trades_df(rows), truncated, oldest)


def strata_rows(items):
    return pd.DataFrame([{"market_id": m, "event_id": ev, "stratum": s, "e": e, "fee_category": "politics"} for m, ev, s, e in items])


def test_c1_same_token_only_and_windows_from_e():
    e = T0
    tr_ok = mk_market(e, 0.50, 0.56)
    # sells on YES in the baseline window but on NO in the final window: not a unit for either token
    mixed = R.Trades(trades_df([(e - 1 * H, "SELL", 5, 0.5, 1), (e - 25 * H, "SELL", 5, 0.5, 0)]))
    u, rep = R.c1_units(strata_rows([("a", "ea", "S", e), ("b", "eb", "S", e)]), {"a": tr_ok, "b": mixed})
    assert set(u["market_id"]) == {"a"} and rep["no_final_prints"] + rep["no_baseline_prints"] >= 2
    assert u["delta"].iloc[0] == pytest.approx(np.mean([0.56, 0.559]) - np.mean([0.50, 0.501]))
    # a print AFTER e (in [e, flip)) is not in the final window
    after = R.Trades(trades_df([(e + 100, "SELL", 5, 0.1, 0), (e - 25 * H, "SELL", 5, 0.5, 0)]))
    u2, _ = R.c1_units(strata_rows([("c", "ec", "S", e)]), {"c": after})
    assert len(u2) == 0


def test_c1_truncated_window_unavailable_and_counted():
    e = T0
    tr = mk_market(e, 0.5, 0.56, truncated=True, oldest=e - 3 * H)  # baseline window starts before the oldest stored trade
    u, rep = R.c1_units(strata_rows([("a", "ea", "S", e)]), {"a": R.Trades(tr.df[tr.df["ts"] > e - 3 * H], True, e - 3 * H)})
    assert len(u) == 0 and rep["baseline_unavailable"] == 1 and rep["baseline_unavailable_candidates"] == 1


def test_matched_contrast_drops_cells_and_clusters_n_by_end_timestamp():
    s = pd.DataFrame({"cell": ["a|d|0"] * 6 + ["b|d|1"] * 2, "event_id": [f"e{i}" for i in range(8)], "delta": [0.05] * 6 + [0.05] * 2, "e": 0.0})
    n = pd.DataFrame({"cell": ["a|d|0"] * 4, "event_id": "x", "delta": [0.0, 0.0, 0.01, 0.01], "e": [1.0, 1.0, 2.0, 2.0]})
    r = R.matched_sn_contrast(s, n, n_boot=200, seed=1)
    assert r["n_cells"] == 1 and r["cells_dropped"] == 1
    assert r["delta_sn"] == pytest.approx(0.05 - 0.005)
    assert r["credit_stage1"] and r["ci90"][0] < r["delta_sn"] < r["ci90"][1] + 1e-9
    none = R.matched_sn_contrast(s, n.assign(cell="zzz"), n_boot=10)
    assert none["n_cells"] == 0 and not none["credit_stage1"]


def test_trade_through_strict_and_optimistic():
    u = pd.DataFrame([{"market_id": "m", "event_id": "e", "token": 0, "tau0": 100.0, "e": 10_000.0, "q": 0.40}])
    at = {"m": R.Trades(trades_df([(200.0, "SELL", 3, 0.40, 0)]))}
    below = {"m": R.Trades(trades_df([(200.0, "SELL", 3, 0.39, 0)]))}
    assert R.c2_paper_bids(u, at).iloc[0]["fill_state"] == 0
    assert R.c2_paper_bids(u, at, optimistic=True).iloc[0]["fill_state"] == 1
    b = R.c2_paper_bids(u, below).iloc[0]
    assert b["fill_state"] == 1 and b["t_fill"] == 200.0
    other_tok = {"m": R.Trades(trades_df([(200.0, "SELL", 3, 0.30, 1)]))}
    assert R.c2_paper_bids(u, other_tok).iloc[0]["fill_state"] == 0
    trunc = {"m": R.Trades(trades_df([(5000.0, "SELL", 3, 0.5, 0)]), True, 5000.0)}
    assert R.c2_paper_bids(u, trunc).iloc[0]["fill_state"] == -1


def test_attach_outcomes_5050_and_censoring():
    bids = pd.DataFrame([{"market_id": f"m{i}", "event_id": f"e{i}", "token": i % 2, "q": 0.4, "fill_state": 1, "t_fill": 0.0, "fill_size": 20.0} for i in range(3)])
    outs = {"m0": {"y0": 0.5, "closed_time": DAY}, "m1": {"y0": 1.0, "closed_time": 2 * DAY}}
    f = R.attach_c2_outcomes(bids, outs, {("m2", 0): 0.35}, censor_mark=9 * DAY)
    assert list(f["Y"]) == [0.5, 0.0, 0.35] and list(f["censored"]) == [False, False, True]
    assert f["net"].iloc[0] == pytest.approx(0.1) and f["w_size"].iloc[0] == 10.0
    assert R.censored_sensitivity(f)["resolution_lag_sensitive"] is True


def test_side_audit_requires_all_four_shares():
    quotes = R.parse_closewin(pd.DataFrame([cw_row("c0", T0, "m", e=T0 + DAY, bid="0.40", ask="0.50")]))  # mid 0.45; recv = T0 + 60
    good = pd.DataFrame([(T0 + 100, "SELL", 0.44, 0), (T0 + 100, "BUY", 0.46, 0), (T0 + 100, "SELL", 0.54, 1), (T0 + 100, "BUY", 0.56, 1)], columns=["ts", "side", "price", "outcome_index"]).assign(market_id="m")
    assert R.side_audit_two_sided(good, quotes)["ok"]
    bad = pd.concat([good, pd.DataFrame([(T0 + 100, "SELL", 0.9, 1)] * 5, columns=good.columns[:4].tolist()).assign(market_id="m")])
    assert not R.side_audit_two_sided(bad, quotes)["ok"]
    assert not R.side_audit_two_sided(good.iloc[:3], quotes)["ok"]  # one share has no prints


def test_g46():
    c1 = pd.DataFrame({"event_id": [f"e{i}" for i in range(120)]})
    c2 = pd.DataFrame({"x": range(400)})
    assert R.g46_gate(c1, c2, 14)["ok"]
    assert not R.g46_gate(c1.iloc[:50], c2, 14)["ok"]
    assert not R.g46_gate(c1, c2.iloc[:50], 14)["ok"]


# ---- statistics helpers + tests -----------------------------------------------------------------------------------------------


def test_lodo_and_decide_semantics():
    assert R.lodo_sign(np.array([1.0, 1.0, -0.5, 1.0]), np.array(list("abcd")))["ok"]
    assert not R.lodo_sign(np.array([1.0, -3.0, 1.0, 1.0]), np.array(list("abcd")))["ok"]  # dropping the day with the big loss would flip... mean stays >0 only without it
    assert not R.lodo_sign(np.array([1.0]), np.array(["a"]))["ok"]
    d = R.decide({"pass_core": True}, {"a": True, "b": None})
    assert not d["advance"] and d["unverified_checks"] == ["b"]
    assert R.decide({"pass_core": True}, {"a": True})["advance"]
    assert not R.decide({"pass_core": True}, {"a": False})["advance"]


def _c1_world(n_events=240, signal=0.05, n_signal=0.0):
    rng = np.random.default_rng(3)
    items, tr, n_items, n_tr = [], {}, [], {}
    for i in range(n_events):
        e = T0 + (i % 40) * 7 * DAY * 0.5 + (i // 40) * 6 * H + i * 3  # spread over 20 weeks, several 6h blocks
        pf = 0.5
        items.append((f"s{i}", f"ev{i}", "S", e))
        tr[f"s{i}"] = mk_market(e, pf, pf + signal + rng.normal(0, 0.01))
        n_items.append((f"n{i}", f"nev{i}", "N", e + 1))
        n_tr[f"n{i}"] = mk_market(e + 1, pf, pf + n_signal + rng.normal(0, 0.01))
    return strata_rows(items), tr, strata_rows(n_items), n_tr


def test_c1_test_advances_with_attribution_and_blocks_without():
    s, st, n, nt = _c1_world(n_signal=0.0)
    c1, _ = R.c1_units(s, st)
    cn, _ = R.c1_units(n, nt)
    # make N share cells with S: same category/day/6h block
    cn = cn.assign(cell=c1["cell"].to_numpy()[: len(cn)] if len(cn) == len(c1) else cn["cell"])
    r = R.c1_test(c1, cn, stage=1, n_boot=0, placebo_draws=1, wb_added=0)
    assert r["testable"] and r["effect"] == pytest.approx(0.05, abs=0.01) and r["p"] < 0.01
    assert r["checks"]["attribution_S_minus_N"] is True
    assert r["advance"], r["failed_checks"] + r["unverified_checks"]
    s2, st2, n2, nt2 = _c1_world(n_signal=0.05)
    c1b, _ = R.c1_units(s2, st2)
    cnb, _ = R.c1_units(n2, nt2)
    cnb = cnb.assign(cell=c1b["cell"].to_numpy())
    rb = R.c1_test(c1b, cnb, stage=1, n_boot=0, placebo_draws=1, wb_added=0)
    assert not rb["advance"] and rb["label"] == "late-life seller discount, not the order stop"


def test_a_c1_week_way_no_longer_makes_c1_untestable():
    # amendment A-C1: 3 ISO weeks (a dev window) used to force p = 1 by construction; the week is now reported only
    s, st, n, nt = _c1_world(n_events=240)
    c1, _ = R.c1_units(s, st)
    c1 = c1.assign(week_e=[f"w{i % 3}" for i in range(len(c1))])
    r = R.c1_test(c1, c1.iloc[:0], stage=1, n_boot=0, placebo_draws=0, wb_added=0)
    assert r["testable"] and r["p"] < 0.01 and set(r["reported"]["sign_by_iso_week"]) == {"w0", "w1", "w2"}
    assert "week" not in (r["p_by_way"] or {}) and R.C_SMALL_G == ("day",)


def test_a_c1_day_way_enters_with_15_days_else_lodo_binds_at_stage_2():
    s, st, n, nt = _c1_world(n_events=240)
    c1, _ = R.c1_units(s, st)
    assert c1["e_day"].nunique() >= 15
    r = R.c1_test(c1, c1.iloc[:0], stage=2, n_boot=0, placebo_draws=0, wb_added=0)
    assert r["time_way"] == "utc_day_small_g" and set(r["p_by_way"]) == {"event", "day"} and "lodo_sign" not in r["checks"]
    assert {"top5_dropped_event", "top5_dropped_day"} <= set(r["checks"])
    few = c1.assign(e_day=[f"2026-10-{11 + i % 14:02d}" for i in range(len(c1))])  # 14 days: the day way cannot enter
    rf = R.c1_test(few, few.iloc[:0], stage=2, n_boot=0, placebo_draws=0, wb_added=0)
    assert rf["testable"] and rf["time_way"].startswith("lodo_binding") and set(rf["p_by_way"]) == {"event"} and "lodo_sign" in rf["checks"]
    assert R.c_pways({"event": np.array(["a"] * 3), "day": np.array(["d1", "d2", "d3"])}).keys() == {"event"}
    # a day-concentrated effect fails the day-way top-5 check and LODO
    bad = c1.assign(delta=np.where(c1["e_day"] == c1["e_day"].iloc[0], 2.0, -0.002))
    rb = R.c1_test(bad, bad.iloc[:0], stage=2, n_boot=0, placebo_draws=0, wb_added=0)
    assert not rb["advance"]


def test_c2_test_gates():
    rng = np.random.default_rng(5)
    n = 240
    f = pd.DataFrame({"event_id": [f"e{i}" for i in range(n)], "week": [f"w{i % 20}" for i in range(n)], "close_day": [f"d{i % 30}" for i in range(n)],
                      "net": 0.15 + rng.normal(0, 0.2, n), "K": 0.4, "d": 3.0, "q": 0.4,
                      "w_size": 10.0, "e": T0 + (np.arange(n) % 30) * DAY, "fill_state": 1, "censored": False})
    allb = f.assign(fill_state=1)
    r = R.c2_test(f, allb, stage=1, n_boot=0, placebo_draws=1)
    assert r["testable"] and r["p"] < 0.01 and r["r_ann"] > 0.1 and r["advance"], (r["failed_checks"], r["unverified_checks"])
    loser = f.assign(net=-0.2 + rng.normal(0, 0.2, n))
    assert not R.c2_test(loser, allb, stage=1, n_boot=0, placebo_draws=1)["advance"]
    # truncation worst case: many unavailable fills added as losers must be able to block
    unavail = pd.DataFrame({"q": [0.4] * 3000, "fill_state": [-1] * 3000})
    assert not R.c2_test(f, pd.concat([allb, unavail]), stage=1, n_boot=0, placebo_draws=1)["advance"]
    # a +0.75c-cost failure
    # The 1.0c floor (> 0.75c) makes the +0.75c route redundant in C2: any mean clearing the floor clears +0.75c, so the old 1.08c case was a correct
    # advance. A mean below the floor must not advance.
    thin = f.assign(net=0.0074 + rng.normal(0, 0.001, n))
    rt = R.c2_test(thin, allb, stage=1, n_boot=0, placebo_draws=1)
    assert not rt["advance"] and rt["checks"]["cost_plus_0.75c"] is False
    assert r["time_way"] == "utc_day_small_g" and set(r["p_by_way"]) == {"event", "day"}


def test_attach_c2_outcomes_sets_close_day():
    bids = pd.DataFrame({"market_id": ["m1"], "token": [0], "fill_state": [1], "q": [0.4], "t_fill": [T0], "fill_size": [5.0], "event_id": ["e"], "e": [T0 + H]})
    f = R.attach_c2_outcomes(bids, {"m1": {"y0": 1.0, "closed_time": T0 + 2 * DAY}}, {}, T0 + 30 * DAY)
    assert f["close_day"].iloc[0] == D.iso(T0 + 2 * DAY)[:10]


# ---- CB4-S ------------------------------------------------------------------------------------------------------------------------


def test_cadence_and_hooks():
    assert R.cadence_class([0, DAY, 2 * DAY]) == "daily" and R.cadence_class([0, 7 * DAY, 14 * DAY]) == "weekly"
    assert R.cadence_class([0, 3 * H, 6 * H]) is None and R.cadence_class([0]) is None


def test_map_trades_buys_and_no_token_mapping():
    tr = trades_df([(1, "BUY", 2, 0.30, 1), (2, "SELL", 3, 0.30, 1), (3, "BUY", 4, 0.60, 0), (4, "SELL", 1, 0.60, 0)])
    ts, buy, px, sz = R.map_trades_to_token(tr, 0)  # rolled-into token = outcome 0
    assert list(buy) == [False, True, True, False] and list(px) == pytest.approx([0.7, 0.7, 0.6, 0.6])
    ts, buy, px, sz = R.map_trades_to_token(tr, 1)
    assert list(buy) == [True, False, False, True] and list(px) == pytest.approx([0.3, 0.3, 0.4, 0.4])


def make_unit(i, series, t0, *, jitter=0.0, high=0.65, low=0.55, flat_before=0.60, cadence="daily", cat="politics", truncated=False, oldest=None, drift_pseudo=False):
    M, V = 3 * H, 12 * H
    o_ps = R.pseudo_origin(t0, V)
    t_a, t_b = o_ps - 4 * H, t0 + V + 4 * H
    ts = np.arange(t_a, t_b, 600.0)
    def f(t):
        if t < t0 - 1 * H:
            base = flat_before + (0.02 * (t - o_ps) / (V) if drift_pseudo and t < o_ps + V + 3 * H else 0.0)
            return base
        return high + jitter if t < t0 + M + 1 * H else low - jitter
    vals = np.array([f(t) for t in ts])
    tr_t = np.arange(t_a, t_b, 300.0)
    px = np.array([f(t) for t in tr_t])
    buy = np.ones(len(tr_t), bool)
    # a trade-through print for S3 right after the ask is posted
    tr_t = np.concatenate([tr_t, tr_t + 1.0, [t0 + 30 * 60.0, t0 + 90 * 60.0]])  # sell prints one cent below the buys; plus the trade-through buy
    px = np.concatenate([px, px - 0.01, [0.70, 0.70]])
    buy = np.concatenate([buy, np.zeros(len(buy), bool), [True, True]])
    o = np.argsort(tr_t)
    # sell prints on a lower level (for the sell-side sign check)
    return R.SuccData(unit_id=f"u{i}", series_id=series, cadence=cadence, category=cat, sports=False, t0=t0, pred_end=t0 + 0.0, succ_created=t0 - 60 * DAY, succ_end=t0 + 10 * DAY, M=M, V=V,
                      ts=ts, vals=vals, tr_ts=tr_t[o], tr_buy=buy[o], tr_px=px[o], tr_size=np.ones(len(tr_t))[o], truncated=truncated, oldest_ts=oldest)


def units_world(n_series=40, per=4, **kw):
    rng = np.random.default_rng(11)
    out = []
    for s in range(n_series):
        for j in range(per):
            out.append(make_unit(len(out), f"s{s}", T0 + (s * 3 + j * 9) * DAY + (s % 5) * H, jitter=float(rng.uniform(-0.01, 0.01)), **kw))
    return out


def test_print_price_uses_buys_only_and_truncation():
    sd = make_unit(0, "s", T0)
    assert R.print_price(sd, T0 + 3 * H, True) == pytest.approx(0.65, abs=0.02)
    assert R.print_price(sd, T0 + 3 * H, False) == pytest.approx(R.print_price(sd, T0 + 3 * H, True) - 0.01, abs=1e-6)  # sells are a separate series
    tr = make_unit(1, "s", T0, truncated=True, oldest=T0 + 2.5 * H)
    assert math.isnan(R.print_price(tr, T0 + 3 * H))  # window starts before the oldest stored trade


def test_pseudo_origin_does_not_overlap_roll_window():
    V = 12 * H
    o = R.pseudo_origin(T0, V)
    assert o + V <= T0 - 6 * H + 1e-9


def test_s3_fill_exit_and_costs():
    sd = make_unit(0, "s", T0)
    r = R.s3_at_origin(sd, sd.t0)
    assert r["state"] == "filled" and r["q"] == pytest.approx(min(0.65 + 0.011 + 0.01, 0.99), abs=0.002)
    assert r["a_x"] == pytest.approx(0.55 + 0.011, abs=0.002)
    r2 = R.s3_at_origin(sd, sd.t0, cost_add=D.COST_SENS_C)
    assert r["net"] - r2["net"] == pytest.approx(D.COST_SENS_C)
    assert r["K"] == pytest.approx(1 - r["q"]) and r["d"] >= 1.0
    # a print AT q does not fill (strict)
    sd2 = make_unit(1, "s", T0)
    sd2.tr_px = np.where(np.isclose(sd2.tr_px, 0.70), r["q"], sd2.tr_px)
    sd2.tr_px = np.minimum(sd2.tr_px, r["q"])
    assert R.s3_at_origin(sd2, sd2.t0)["state"] == "not_filled"


def test_unit_eligibility_rules():
    sd = make_unit(0, "s", T0)
    assert R.unit_eligible(sd, sd.t0) == (True, "ok")
    sd.succ_end = sd.t0 + 13 * H
    assert R.unit_eligible(sd, sd.t0)[1] == "succ_end_before_horizon"
    sd = make_unit(0, "s", T0)
    sd.succ_created = sd.t0 - 0.5 * H
    assert R.unit_eligible(sd, sd.t0)[1] == "succ_created_too_late"
    sd = make_unit(0, "s", T0, truncated=True, oldest=T0)
    assert R.unit_eligible(sd, sd.t0) == (True, "ok")  # truncation keeps the unit with P_A missing (fix 5)
    assert not sd.prints_available and math.isnan(R.s2_value(sd, sd.t0, "ask")["neg_v"]) and np.isfinite(R.s2_value(sd, sd.t0, "hist")["neg_v"])
    assert R.s3_at_origin(sd, sd.t0)["state"] == "unavailable"
    ok = make_unit(0, "s", T0, truncated=True, oldest=R.pseudo_origin(T0, make_unit(0, "s", T0).V) - 3 * H)
    assert ok.prints_available  # oldest stored trade at t0' - 3h is enough
    df = R.s_values([sd])["df"]
    assert len(df) == 1 and not np.isfinite(df["neg_v"].iloc[0])
    wc = R._s2_worst_case([sd], df)
    assert wc["added"] == 1 and np.isfinite(wc["mean"])  # added back on the history-price series


def test_s_tests_advance_and_attribution_blocks_drift():
    units = units_world()
    res = R.s_tests(units, stage=1, n_boot=0, placebo_draws=1)
    s2 = res["tests"]["S2"]
    assert s2["testable"] and s2["effect"] == pytest.approx(0.10, abs=0.01) and s2["p"] < 0.01
    assert s2["attribution"]["credit"] and s2["advance"], (s2["failed_checks"], s2["unverified_checks"])
    s3 = res["tests"]["S3"]
    assert s3["testable"] and s3["effect"] > 0.05 and s3["advance"], (s3["failed_checks"], s3["unverified_checks"])
    # a pseudo-origin that shows the same reversal (generic drift) removes the credit
    drift = units_world()
    for u in drift:
        o = R.pseudo_origin(u.t0, u.V)
        u.tr_px = np.where((u.tr_ts >= o) & (u.tr_ts < o + u.V + 1 * H) & (u.tr_ts > o + u.M + 0.5 * H), 0.50, u.tr_px)
        u.tr_px = np.where((u.tr_ts >= o) & (u.tr_ts <= o + u.M + 0.5 * H), 0.60, u.tr_px)
    rd = R.s_tests(drift, stage=1, n_boot=0, placebo_draws=1)["tests"]["S2"]
    assert rd["attribution"]["pseudo_mean"] > 0.05 and not rd["attribution"]["credit"] and not rd["advance"]
    assert rd["label"] == "generic drift of the winning side, not the roll"


def test_s2_pseudo_attribution_unverified_below_minimum_and_missing_by_cadence():
    units = units_world(n_series=5, per=2)
    df = R.s_values(units)["df"]
    att = R.pseudo_roll_attribution(units, df[np.isfinite(df["neg_v"])])
    assert not att["verified"] and not att["credit"] and att["n_both"] <= 10
    u = make_unit(0, "s", T0, cadence="daily")
    u.succ_created = R.pseudo_origin(u.t0, u.V) - 0.5 * H  # created after t0' - 1h: no pseudo-origin
    df = R.s_values([u])["df"]
    att = R.pseudo_roll_attribution([u], df)
    assert att["n_both"] == 0 and att["missing_pseudo_by_cadence"] == {"daily": 1}


def test_alt_origin_disagreement_blocks():
    units = units_world()
    for u in units:  # alt origin = endDate + 1h, set so that the alt-window shows the opposite sign (price rises through V)
        u.pred_end = u.t0 + 30 * H
        u.succ_end = u.t0 + 80 * H
        u.ts = np.concatenate([u.ts, np.arange(u.ts[-1] + 600, u.t0 + 60 * H, 600.0)])
        u.vals = np.concatenate([u.vals, np.linspace(0.55, 0.75, len(u.ts) - len(u.vals))])
        extra_t = np.arange(u.tr_ts[-1] + 300, u.t0 + 60 * H, 300.0)
        u.tr_ts = np.concatenate([u.tr_ts, extra_t])
        u.tr_buy = np.concatenate([u.tr_buy, np.ones(len(extra_t), bool)])
        u.tr_px = np.concatenate([u.tr_px, np.linspace(0.55, 0.75, len(extra_t))])
        u.tr_size = np.concatenate([u.tr_size, np.ones(len(extra_t))])
    r = R.s_tests(units, stage=1, n_boot=0, placebo_draws=1)["tests"]["S2"]
    assert r["checks"]["alt_origin_sign"] is False and not r["advance"]


def test_era_rule_switches_only_with_register_and_requires_post_subset():
    df = pd.DataFrame({"era_rule": ["pooled_allowed"] * 3, "post_rollout": [False, False, True], "neg_v": [0.1, 0.1, -0.1]})
    assert R.era_subset_rule(df, "neg_v") is True
    df2 = df.assign(era_rule="post_rollout_or_interaction")
    assert R.era_subset_rule(df2, "neg_v") is False
    assert R.era_subset_rule(df2.assign(post_rollout=False), "neg_v") is None


def test_publicity_check_reads_prices_and_trades_only_and_stops_below_95():
    ts = np.arange(0, 7200, 600.0)
    prices = {f"u{i}": (ts, np.full(len(ts), 0.99 if i < 98 else 0.5)) for i in range(100)}
    trades = {f"u{i}": np.array([10.0]) for i in range(100)}
    t0 = {f"u{i}": 1000.0 for i in range(100)}
    r = R.t0_publicity_check(trades, prices, t0)
    assert r["ok"] and r["share_price_converged"] == pytest.approx(0.98)
    late = dict(trades)
    for i in range(10):
        late[f"u{i}"] = np.array([10.0, 2000.0])  # a trade after t0
    assert not R.t0_publicity_check(late, prices, t0)["ok"]


def test_side_audit_history_75_percent():
    sd = make_unit(0, "s", T0)
    t = T0 + 5 * H
    p = float(R.hist_price(sd, t))
    rows = [(t, "BUY", 1, p + 0.01, 0), (t, "SELL", 1, p - 0.01, 0), (t, "BUY", 1, 1 - p + 0.01, 1), (t, "SELL", 1, 1 - p - 0.01, 1)]
    ok = R.side_audit_history([sd], {sd.unit_id: trades_df(rows)}, {sd.unit_id: 0})
    assert ok["ok"]
    bad = R.side_audit_history([sd], {sd.unit_id: trades_df(rows[:3] + [(t, "SELL", 1, 0.99, 1)])}, {sd.unit_id: 0})
    assert not bad["ok"]


def test_g50_and_split_wrapper_deterministic_and_data_free():
    units = units_world()
    assert not R.g50_gate(units)["ok"]  # 160 units < 300
    us = [{"unit_id": f"u{i}", "t0_epoch": T0 + i * 3 * H, "t0_date": ""} for i in range(300)]
    a, b = R.split_h7s(us), R.split_h7s(us)
    assert a == b and not (set(a["screen"]) & set(a["holdout"])) and not (set(a["embargo"]) & set(a["holdout"]))
    assert len(a["holdout"]) <= 0.40 * 300 + 1


def test_random_origin_placebo_runs_and_is_bounded():
    units = units_world(n_series=35, per=3)
    res = R._s3_random_origin_placebo(units, pd.DataFrame(), alpha=0.01, draws=3, seed=1)
    assert res["n_draws"] == 3 and res["advance_rate"] <= 1.0


def test_censored_fill_without_last_bid_is_unavailable_not_silent_nan():
    bids = pd.DataFrame([{"market_id": "m0", "event_id": "e0", "token": 0, "q": 0.4, "fill_state": 1, "t_fill": 0.0, "fill_size": 20.0, "e": 5.0}])
    f = R.attach_c2_outcomes(bids, {}, {}, censor_mark=9 * DAY)  # unresolved, no recorded bid
    assert bool(f["unavailable_censored"].iloc[0]) and not np.isfinite(f["Y"].iloc[0])
    res = R.c2_test(f, bids, stage=1, n_boot=0, placebo_draws=0)
    assert res["censored_unavailable"] == 1 and res["testable"] is False
    ok = R.attach_c2_outcomes(bids, {}, {("m0", 0): 0.3}, censor_mark=9 * DAY)
    assert not ok["unavailable_censored"].any()


def test_s_census_counts_no_values_and_pseudo_by_cadence(monkeypatch):
    units = units_world(n_series=5, per=2) + [make_unit(99, "sT", T0, truncated=True, oldest=T0)]
    # the census must never call the value functions
    for name in ("s2_value", "s_values", "s3_at_origin", "print_price"):
        monkeypatch.setattr(R, name, lambda *a, _n=name, **k: (_ for _ in ()).throw(AssertionError(_n)))
    c = R.s_census_counts(units)
    daily = c["by_cadence"]["daily"]
    assert daily["units"] == 11 and daily["truncated"] == 1 and daily["pa_both"] <= daily["eligible"]
    assert daily["pseudo_origin_available"] + daily["pseudo_origin_missing"] == daily["pa_both"]
    assert c["G_series"] <= 5 and "G_series_x_week" in c
    assert set(R.g50_gate(units)) == {"series", "units", "ok"}


def test_e_predicted_mde_uses_declared_scaling():
    rows = {k: 8000 for k in ("SP0", "SP1", "SP2", "OP0", "OP1", "OP2")}
    ev = {k: 2000 for k in rows}
    from astrolabe.research_lab import cb4_measure as M

    m = M.e_predicted_mde(rows, ev)
    assert 0.5 < m["E1_cents_per_sd"]["mde"] < 0.9 and 0.4 < m["E2_cents_per_print"]["mde"] < 0.8  # doc: about 0.6-0.8c per SD, about 0.6c per print
    assert M.e_predicted_mde({"SP0": 0}, {}, halves=False)["E1_cents_per_sd"] is None


def test_s2_worst_case_adds_back_only_truncated_units():
    """Freeze-check fix 7: a unit whose P_A window has no print but whose history is complete is not 'unavailable' and is not added back."""
    trunc = make_unit(0, "s", T0, truncated=True, oldest=T0)
    gap = make_unit(1, "s2", T0)
    keep = ~((gap.tr_ts >= gap.t0 + gap.V - H) & (gap.tr_ts < gap.t0 + gap.V))  # no print in the V_end window, untruncated
    gap.tr_ts, gap.tr_buy, gap.tr_px, gap.tr_size = gap.tr_ts[keep], gap.tr_buy[keep], gap.tr_px[keep], gap.tr_size[keep]
    df = R.s_values([trunc, gap])["df"]
    assert list(df["prints_truncated"]) == [True, False] and not np.isfinite(df["neg_v"]).any()
    wc = R._s2_worst_case([trunc, gap], df)
    assert wc["added"] == 1


def _c2_frame(n=240, days=30, net=0.15, seed=5):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({"event_id": [f"e{i}" for i in range(n)], "week": [f"w{i % 20}" for i in range(n)], "close_day": [f"2026-11-{1 + i % days:02d}" for i in range(n)],
                         "net": net + rng.normal(0, 0.2, n), "K": 0.4, "d": 3.0, "q": 0.4, "w_size": 10.0, "e": T0 + (np.arange(n) % 30) * DAY, "fill_state": 1,
                         "censored": False, "market_id": [f"m{i}" for i in range(n)], "token": 0})


def test_m3_c2_lodo_binds_by_closing_day_and_by_day_of_e():
    f = _c2_frame(days=10)  # closing days < 15: the day way does not enter, LODO binds at Stage 2 on both clocks
    r = R.c2_test(f, f, stage=2, n_boot=0, placebo_draws=0)
    assert r["time_way"].startswith("lodo_binding") and {"lodo_sign_close_day", "lodo_sign_e_day"} <= set(r["checks"]) and "lodo_sign" not in r["checks"]
    assert r["checks"]["lodo_sign_close_day"] and r["checks"]["lodo_sign_e_day"]
    # an effect carried by one closing day fails the closing-day LODO even though the day-of-e LODO holds
    g = f.assign(net=np.where(f["close_day"] == "2026-11-01", 3.0, -0.05))
    rg = R.c2_test(g, g, stage=2, n_boot=0, placebo_draws=0)
    assert rg["checks"]["lodo_sign_close_day"] is False and not rg["advance"]
    assert isinstance(r["reported"]["daily_lag1_autocorr"], float)


def test_top5_day_branch_below_15_days_needs_lodo():
    # 17 days: five large negative days (the top 5 by |contribution|), one positive day B that carries the rest, eleven slightly negative days.
    # Dropping the top 5 days leaves 12 < 15 days: the day way cannot enter, so the branch must also pass LODO, which fails because B carries it.
    vals, day = [], []
    for d in range(5):
        vals += [-2.0] * 10
        day += [f"A{d}"] * 10
    vals += [1.5] * 10
    day += ["B"] * 10
    for d in range(11):
        vals += [-0.05] * 10
        day += [f"C{d:02d}"] * 10
    v, day = np.array(vals), np.array(day)
    ways = {"event": np.array([f"e{i}" for i in range(len(v))]), "day": day}
    plain = R.top_clusters_dropped(v, ways, floor=0.0, alpha=0.5, small_g_ways=R.C_SMALL_G, pways=R.c_pways)
    with_lodo = R.top_clusters_dropped(v, ways, floor=0.0, alpha=0.5, small_g_ways=R.C_SMALL_G, pways=R.c_pways, lodo_days=[day])
    assert plain["day"] is True and with_lodo["day"] is False


def test_m2_closed_not_decisive_fill_is_unavailable_not_censored():
    bids = pd.DataFrame({"market_id": ["m1", "m2"], "token": [0, 0], "fill_state": [1, 1], "q": [0.4, 0.4], "t_fill": [T0, T0], "fill_size": [5.0, 5.0],
                         "event_id": ["e1", "e2"], "e": [T0 + H, T0 + H]})
    outs = {"m1": {"y0": None, "closed_time": T0 + DAY, "status": "closed_not_decisive"}, "m2": {"y0": None, "closed_time": None, "status": "unresolved"}}
    f = R.attach_c2_outcomes(bids, outs, {("m1", 0): 0.5, ("m2", 0): 0.5}, T0 + 30 * DAY)
    assert list(f["closed_not_decisive"]) == [True, False] and list(f["censored"]) == [False, True]
    assert list(f["unavailable_censored"]) == [True, False] and f["Y"].iloc[1] == 0.5
