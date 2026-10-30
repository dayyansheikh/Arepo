# ruff: noqa: E501
"""M2 (CH264) code tests, part 2: J3 (read-out fetch), the estimands, the bootstrap, the cells, the hazard, the bound, the coarse and void rules and the analysis
refusals of MEASUREMENT_M2_CH264.md sections 4-8, 10, 11 and 9.4-9.5. Synthetic tmp trees only (never the host dumps)."""

from __future__ import annotations

import copy
import gzip
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy.stats import beta

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_m2_code as tc  # noqa: E402
import test_m2_j1 as t1  # noqa: E402

from astrolabe.research_lab import m2_analysis as an  # noqa: E402
from astrolabe.research_lab import m2_j2 as cl  # noqa: E402
from astrolabe.research_lab import m2_readout as ro  # noqa: E402
from astrolabe.research_lab import m2_spec as sp  # noqa: E402

SPEC = tc.SPEC
RO_T = sp.ts(SPEC, "readout_utc")
CELLS_OK = {"S1": "mid", "S2": "barrier", "S3": "other", "S4": "fee_free", "S5": "YES", "S6": "(0.7,0.8]", "S7": "no", "S8": "1", "S9": "0.001", "S10": "days 1-7", "S11": "(0.01,0.03]", "S12": "mid|barrier"}


# --- a fake Gamma ----------------------------------------------------------------------------------------------------------------------

def rec(mid, closed=True, uma="resolved", prices=("1", "0"), closed_time="2026-10-21 03:00:00+00", end="2026-10-20T10:00:00Z"):
    return {"id": str(mid), "closed": closed, "umaResolutionStatus": uma, "outcomePrices": json.dumps(list(prices)), "closedTime": closed_time, "endDate": end}


class Gamma:
    """get(params) -> (list, 'ok') like the polite fetcher. ``closed=true`` returns only closed records. ``fail`` ids make a request fail (None)."""

    def __init__(self, db: dict, fail=()):
        self.db, self.fail, self.calls = db, set(fail), []

    def __call__(self, params):
        ids = [int(v) for k, v in params if k == "id"]
        closed = ("closed", "true") in params
        self.calls.append((tuple(ids), closed))
        if self.fail & set(ids):
            return None, "http_500"
        return [r for i in ids if (r := self.db.get(i)) is not None and (not closed or r["closed"])], "ok"


class Clock:
    def __init__(self, t0):
        self.t, self.slept = t0, []

    def __call__(self):
        self.t += 1.0
        return self.t

    def sleep(self, s):
        self.slept.append(s)
        self.t += s


# --- J3 ----------------------------------------------------------------------------------------------------------------------------------

def test_classify_record_not_closed_is_pending_for_every_final_state_and_y_is_null():
    a = ro.classify_record(rec(1, closed=False))
    assert a["state"] == "pending" and a["y"] is None and a["parse_reason"] == "not_closed" and a["sub_class"] == "not_closed"
    b = ro.classify_record(rec(1, closed=False, prices=("0.5", "0.5")))  # split on an open record: still pending, not a final state
    assert b["state"] == "pending" and b["y"] is None
    assert ro.classify_record(rec(1, closed=True, prices=("0.5", "0.5")))["state"] == "split_50_50"
    c = ro.classify_record(rec(1, closed=True, uma=""))
    assert c["state"] == "pending" and c["sub_class"] == "closed_not_uma_resolved"
    assert ro.classify_record(rec(1, prices=("0.7", "0.3")))["state"] == "unavailable_other_price_vector"
    assert ro.classify_record(rec(1, prices=("x",)))["state"] == "unavailable_bad_prices"
    ok = ro.classify_record(rec(1, prices=("0", "1")))
    assert ok["state"] == "resolved" and ok["y"] == 0 and ok["closed_time"] and ok["end_date"] and ok["uma"] == "resolved"


def fetch(ids, db, fail=(), spec=SPEC):
    g, clk = Gamma(db, fail), Clock(1.0e9)
    recs, req = ro.fetch_markets(ids, g, spec, clk.sleep, clk)
    return recs, req, g, clk


def test_fetch_passes_pending_vs_absence_and_the_single_id_requery():
    db = {1: rec(1), 2: rec(2, closed=False), 3: rec(3, closed=True, uma="")}
    recs, req, g, _ = fetch([1, 2, 3, 4], db)
    assert recs[1]["state"] == "resolved" and recs[1]["fetch_pass"] == "closed_true"
    assert recs[2]["state"] == "pending" and recs[2]["fetch_pass"] == "no_closed_filter"  # found only without the closed filter
    assert recs[3]["state"] == "pending" and recs[3]["sub_class"] == "closed_not_uma_resolved"
    assert recs[4]["state"] == "not_found" and recs[4]["fetch_pass"] == "single_id_both_empty"
    assert req["single_id"] == 2  # alone, with and without closed=true
    assert ((4,), True) in g.calls and ((4,), False) in g.calls


def test_not_found_needs_two_http_200_answers_a_failed_single_query_is_unavailable():
    class Flaky(Gamma):
        def __call__(self, params):
            ids = [v for k, v in params if k == "id"]
            if ids == ["4"] and ("limit", "1") in params and ("closed", "true") not in params:  # the single query without the closed filter always fails
                return None, "http_500"
            return super().__call__(params)

    g, clk = Flaky({}), Clock(1.0e9)
    recs, _ = ro.fetch_markets([4], g, SPEC, clk.sleep, clk)
    assert recs[4]["state"] == "unavailable_fetch" and recs[4]["fetch_pass"] == "single_id_failed"
    # a record found by the single query wins (a batch listing can miss it)
    g2, clk2 = Gamma({4: rec(4, closed=False)}), Clock(1.0e9)

    class BatchBlind(Gamma):
        def __call__(self, params):
            return ([], "ok") if sum(1 for k, _ in params if k == "id") > 1 else super().__call__(params)

    g3 = BatchBlind({4: rec(4, closed=False)})
    recs3, _ = ro.fetch_markets([4, 5], g3, SPEC, clk2.sleep, clk2)
    assert recs3[4]["state"] == "pending" and recs3[4]["fetch_pass"] == "single_id_open" and recs3[5]["state"] == "not_found"
    del g2


def test_a_failing_batch_retries_three_times_at_least_one_hour_apart_then_is_unavailable_fetch():
    recs, req, _g, clk = fetch([1, 2], {1: rec(1), 2: rec(2)}, fail={1})
    assert recs[1]["state"] == "unavailable_fetch" and recs[2]["state"] == "unavailable_fetch" and req["closed_true"] == 3  # one batch of two, three attempts
    assert len(clk.slept) == 2 and all(s >= SPEC["fetch"]["attempt_gap_s"] - 10 for s in clk.slept)
    assert recs[1]["attempts"] == 3


def test_batches_of_fifty():
    db = {i: rec(i) for i in range(1, 121)}
    _, req, g, _ = fetch(list(range(1, 121)), db)
    assert req["closed_true"] == 3 and [len(c[0]) for c in g.calls] == [50, 50, 20]


def build_world(tmp, mutate=None, spec=SPEC):
    """J1 over the synthetic captures (market 1 proposed from capture 12, market 2 closes at 13, market 5 vanishes at 11), J2 manifests, J3 with a fake Gamma."""
    snap = tmp / "research_lab" / "snapshots"
    for k in range(t1.N):
        m = t1.markets(k)
        if k >= 12:
            m[1] = dict(m[1], uma='["proposed"]')
        if k >= 13:
            m[2] = dict(m[2], closed="true")
        if k >= 11:
            m.pop(5)
        t1.write_capture(snap, k, m)
    rr = tmp / "research_lab" / "stream_gamma_rules"
    t1.write_rules(rr)
    st = tmp / "research_lab" / "m2_ch264"
    tc.run(snap, rr, st, spec=spec)
    man = cl.close_units(st, spec, now=sp.ts(spec, "end_utc") + 7 * 3600.0)
    fman = cl.close_followup(st, spec, now=sp.ts(spec, "readout_utc") + 60.0)
    db = {1: rec(1), 2: rec(2, prices=("0", "1")), 5: rec(5, prices=("1", "0")), 6: rec(6, prices=("0.5", "0.5")), 11: rec(11, closed=False), 13: rec(13, uma=""),
          14: rec(14), 25: rec(25, prices=("0.7", "0.3")), 4: rec(4, closed_time="2026-10-21 05:00:00+00")}
    if mutate:
        mutate(db)
    gam = Gamma(db)
    clk = Clock(sp.ts(spec, "readout_utc") + 100.0)
    jm = ro.run_j3(st, gam, spec, now=sp.ts(spec, "readout_utc") + 100.0, sleep=clk.sleep, clock=clk)
    pins = {"spec_sha": sp.spec_sha(spec), "code_sha": sp.code_sha(), "registration_commit_utc": "2026-10-01T00:00:00Z", "manifest_sha256": man["manifest_sha256"],
            "followup_manifest_sha256": fman["manifest_sha256"]}
    return snap, rr, st, man, fman, jm, pins


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("w")
    snap, rr, st, man, fman, jm, pins = build_world(tmp)
    out = tmp / "research_lab" / "OUT.json"
    res = an.run_analysis(st, pins, out, SPEC, now=RO_T + 13 * 3600.0, m1_store=None)
    return {"tmp": tmp, "snap": snap, "st": st, "man": man, "fman": fman, "jm": jm, "pins": pins, "res": res, "out": out}


def test_j3_writes_the_readout_with_no_favourite_markets_and_is_write_once(world):
    jm, st = world["jm"], world["st"]
    assert jm["unit_markets"] == 9 and jm["no_favourite_markets"] == 1 and jm["markets"] == 10
    assert jm["counts_units"] == {"not_found": 1, "pending": 2, "resolved": 4, "split_50_50": 1, "unavailable_other_price_vector": 1}
    assert jm["counts_no_favourite"] == {"resolved": 1}
    ro_rows = {r["market_id"]: r for r in (json.loads(x) for x in gzip.open(st / "readout" / "readout.jsonl.gz", "rt"))}
    assert ro_rows[4]["group"] == "no_favourite" and ro_rows[1]["group"] == "unit" and ro_rows[11]["y"] is None and ro_rows[11]["state"] == "pending"
    with pytest.raises(sp.M2Refusal, match="overwrite"):
        ro.run_j3(st, Gamma({}), SPEC, now=RO_T + 100.0)


def test_j3_refusals(tmp_path):
    snap, rr = t1.build(tmp_path)
    st = tmp_path / "research_lab" / "m2_ch264"
    tc.run(snap, rr, st)
    with pytest.raises(sp.M2Refusal, match="before READOUT_UTC"):
        ro.run_j3(st, Gamma({}), SPEC, now=RO_T - 60.0)
    with pytest.raises(sp.M2Refusal, match="no J2 unit manifest"):
        ro.run_j3(st, Gamma({}), SPEC, now=RO_T + 60.0)
    cl.close_units(st, SPEC, now=sp.ts(SPEC, "end_utc") + 7 * 3600.0)
    with pytest.raises(sp.PinMismatch):
        ro.run_j3(st, Gamma({}), SPEC, now=RO_T + 60.0, pins={"spec_sha": "x", "code_sha": "y"})


# --- the analysis on the synthetic world ---------------------------------------------------------------------------------------------------

def test_headline_theta_theta_nf_and_the_band_equal_hand_computation(world):
    res, st = world["res"], world["st"]
    us = {u["market_id"]: u for u in t1.read_units(st)}
    n = lambda m, q: q - us[m]["ask_f"] - us[m]["fee_l1"]  # noqa: E731
    fin = [n(1, 1.0), n(2, 1.0), n(5, 0.0), n(6, 0.5), n(14, 1.0)]  # 5: NO side, outcome 0 won (y = 1) -> the other side
    th = sum(fin) / 5
    assert res["classes"] == {"not_found": 1, "pending": 2, "resolved_favoured": 3, "resolved_other": 1, "split_50_50": 1, "unavailable_other_price_vector": 1}
    assert res["final_units"] == 5 and res["eligible_units"] == 9 and res["void"] is False
    assert res["headline_ci"]["theta"]["est"] == pytest.approx(th, abs=1e-12)
    loss12 = n(12, 0.0)
    assert res["headline_ci"]["theta_NF"]["est"] == pytest.approx((sum(fin) + loss12) / 6, abs=1e-12)
    nonfinal = [11, 12, 13, 25]
    assert res["band"]["theta_W"] == pytest.approx((sum(fin) + sum(n(m, 0.0) for m in nonfinal)) / 9, abs=1e-12)
    assert res["band"]["theta_B"] == pytest.approx((sum(fin) + sum(n(m, 1.0) for m in nonfinal)) / 9, abs=1e-12)
    assert res["band"]["theta_W"] < res["headline_ci"]["theta"]["est"] < res["band"]["theta_B"]
    comp = res["headline_components"]
    assert comp["q_eff"]["est"] == pytest.approx((3 + 0.5) / 5) and comp["p_win"]["est"] == pytest.approx(3 / 5) and comp["p_loss"]["est"] == pytest.approx(1 / 5) and comp["p_split"]["est"] == pytest.approx(1 / 5)
    assert comp["mid_f"]["est"] == pytest.approx(sum(us[m]["mid_f"] for m in (1, 2, 5, 6, 14)) / 5)
    assert comp["h"]["est"] == pytest.approx(sum(us[m]["half_spread"] for m in (1, 2, 5, 6, 14)) / 5)
    assert comp["pi"]["est"] == pytest.approx(comp["q_eff"]["est"] - comp["mid_f"]["est"])
    assert res["identity"]["ok"] and res["identity"]["theta_minus_pi_plus_h_plus_fee"] <= 1e-9  # checked within 1e-9, never with ==
    assert res["theta_L2"]["est"] == pytest.approx(sum(1.0 * (q) - us[m]["ask_f"] - us[m]["fee_l2"] for m, q in ((1, 1), (2, 1), (5, 0), (6, .5), (14, 1))) / 5)
    assert res["theta_cap"]["est"] <= res["headline_ci"]["theta"]["est"]
    # theta_E: event weights (events: eA holds 1, 2, 6; 5 and 14 alone)
    e_means = [(n(1, 1.0) + n(2, 1.0) + n(6, 0.5)) / 3, n(5, 0.0), n(14, 1.0)]
    assert res["theta_E"]["est"] == pytest.approx(sum(e_means) / 3)


def test_ledger_line_wording_and_flags(world):
    res = world["res"]
    line = res["ledger_line"]
    assert line.startswith("measured (prospective, k = 0; units seen at their first overdue 2 h capture, open, unproposed, two-sided and interior at k): theta = ")
    for part in ("theta_NF = ", "band [theta_W, theta_B]", "cost-model-v1, conservative fee, touch, size-unlimited", "capacity unavailable (no book is read for past-end markets)", "[reported coarse]"):
        assert part in line
    assert not an.BANNED.search(json.dumps(res, default=str)) and "p-value" not in json.dumps(res)
    assert res["coarse"]["coarse"] and res["coarse"]["rules_fired"]["1_final_units_below"] and res["coarse"]["rules_fired"]["3_nonfinal_share_above"]
    assert res["capacity"] == "unavailable (no book is read for past-end markets, 5.3)"


def test_event_bound_strata_and_the_clopper_pearson_level(world):
    b = world["res"]["event_bound"]
    level = 1 - 0.05 / 4
    # basis: 5 final + not_found market 12 = 6 units; events: eA (1, 2, 6: split flagged), e5, e14, e12 (not_found flagged)
    assert b["N_D"] == 6 and b["E_D"] == 4 and b["level"] == level
    s1, s23 = b["strata"]["1"], b["strata"]["2-3"]
    assert (s1["events"], s1["units"], s1["flagged_events"]) == (3, 3, 1) and (s23["events"], s23["units"], s23["flagged_events"]) == (1, 3, 1)
    assert s1["p_upper"] == pytest.approx(float(beta.ppf(level, 2, 2))) and s23["p_upper"] == 1.0  # all events flagged: the bound is 1
    assert b["strata"]["4-9"]["p_upper"] == 0.0 and b["strata"]["10+"]["events"] == 0  # a stratum with no events contributes 0
    assert b["B_U"] == pytest.approx(3 / 6 * s1["p_upper"] + 3 / 6 * 1.0)
    assert b["ten_largest_events"][0]["basis_units"] == 3 and "homogeneity" in b["assumption"]
    assert world["res"]["pending_unavailable_outside_bound_basis"] == 3  # 2 pending + 1 unavailable


def test_event_bound_with_zero_flags_matches_the_lower_limit_arithmetic():
    spec = SPEC
    basis = [{"event_id": f"e{i}", "cls": "resolved_favoured"} for i in range(40)]
    b = an.event_bound(basis, spec)
    assert b["B_U"] == pytest.approx(float(beta.ppf(1 - 0.05 / 4, 1, 40)), rel=1e-12) == pytest.approx(1 - 0.0125 ** (1 / 40), rel=1e-9)
    assert b["B_U"] == pytest.approx(4.38 / 40, rel=0.1)  # with zero flags the bound is about 4.38 / E (text 7.2)
    assert an.event_bound([], spec)["B_U"] is None


def test_cells_cover_all_12_splits_and_69_declared_cells(world):
    sps = world["res"]["splits"]
    assert list(sps) == list(an.SPLITS) and sum(1 for s in sps.values() for c in s if not c.startswith("_unlisted")) == 69
    assert {k: len([c for c in v if not c.startswith("_unlisted")]) for k, v in sps.items()} == {"S1": 4, "S2": 6, "S3": 10, "S4": 3, "S5": 2, "S6": 5, "S7": 2, "S8": 3, "S9": 3, "S10": 3, "S11": 4, "S12": 24}
    s2 = sps["S2"]
    assert s2["scheduled"]["N"] == 1 and s2["scheduled"]["thin"] is True and s2["rules_unresolved"]["N"] == 1 and s2["no_rules"]["N"] == 4
    assert sum(c["N"] for c in s2.values()) == 9 and sum(c["N"] for c in sps["S5"].values()) == 9
    cell = sps["S5"]["YES"]
    assert set(cell) >= {"N", "events", "final", "final_events", "q_eff", "mid_f", "h", "fee_l1", "theta", "theta_NF", "nonfinal", "thin"}
    assert cell["theta"]["est"] is not None and sps["S1"]["na"]["theta"]["est"] is None and sps["S1"]["na"]["N"] == 0  # an empty cell is printed, not dropped


def test_contrasts_are_differences_within_the_same_draws(world):
    c = world["res"]["contrasts"]
    assert set(c) == {"D1", "D2", "note"} and set(c["D1"]) == {"theta", "pi", "proposal_incidence_24h"} and set(c["D2"]) == {"theta", "pi"}
    s = world["res"]["splits"]
    d2 = c["D2"]["theta"]["est"]
    assert d2 == pytest.approx(s["S2"]["scheduled"]["theta"]["est"] - s["S2"]["barrier"]["theta"]["est"])
    assert c["D1"]["theta"]["est"] is None or c["D1"]["theta"]["est"] == pytest.approx(s["S1"]["high"]["theta"]["est"] - s["S1"]["low"]["theta"]["est"])
    assert "ambiguity" in c["note"] and c["D1"]["proposal_incidence_24h"] is not None


def test_cr1_se_day_block_and_bootstrap_block(world):
    res = world["res"]
    st = world["st"]
    us = {u["market_id"]: u for u in t1.read_units(st)}
    vals = np.array([1.0 - us[m]["ask_f"] - us[m]["fee_l1"] if m != 5 else 0.0 - us[5]["ask_f"] - us[5]["fee_l1"] for m in (1, 2, 5, 14)] + [0.5 - us[6]["ask_f"] - us[6]["fee_l1"]])
    ev = np.array([0, 0, 1, 2, 0])  # markets 1, 2, 6 share eA
    ordered = np.array([vals[0], vals[1], vals[4], vals[2], vals[3]])
    ev_ord = np.array([0, 0, 0, 1, 2])
    ref = an.cr1_se(ordered, ev_ord)
    assert res["cr1_event_clustered_se"]["theta"]["se"] == pytest.approx(ref["se"]) and res["cr1_event_clustered_se"]["theta"]["clusters"] == 3
    m = ordered.mean()
    g = np.array([(ordered[:3] - m).sum(), ordered[3] - m, ordered[4] - m])
    assert ref["se"] == pytest.approx(math.sqrt(3 / 2 * (g ** 2).sum()) / 5)
    assert res["day_block_bootstrap"]["theta"]["days"] >= 1 and res["day_block_bootstrap"]["wider_interval_for_theta"] in ("event_bootstrap", "day_block_bootstrap")
    b = res["bootstrap"]
    assert (b["B"], b["seed"]) == (10000, 20261125) and res["headline_ci"]["theta"]["draws_used"] > 0
    ev_ = del_ = None
    del ev, ev_, del_


def test_proposal_hazard_competing_risks_by_hand(world):
    hz = world["res"]["proposal_hazard"]
    g = hz["groups"]["all"]
    # 9 units, k at capture 10. m1: P at j=12 (T=2). m5: absent at j=11 (C, T=1). m2: closed at j=13 (C, T=3). the other six: censored at T=5.
    assert g["hazard_P_per_slot"]["1"]["at_risk"] == 9 and g["hazard_P_per_slot"]["1"]["est"] == 0.0
    assert g["hazard_P_per_slot"]["2"]["est"] == pytest.approx(1 / 8) and g["hazard_P_per_slot"]["2"]["at_risk"] == 8
    assert g["cif_P"]["6h"]["est"] == pytest.approx(1 / 9) and g["cif_C"]["6h"]["est"] == pytest.approx(2 / 9)
    assert g["cif_P"]["24h"]["est"] == pytest.approx(1 / 9) and g["cif_P"]["30d"]["est"] == pytest.approx(1 / 9)  # nobody at risk after 5 slots: carried, not extrapolated
    assert hz["final_units_without_P_ever_seen"] == pytest.approx(4 / 5)
    assert set(hz["groups"]) == {"all", "S1=low", "S1=mid", "S1=high", "S1=na", "S2=scheduled", "S2=barrier", "S2=both", "S2=other", "S2=no_rules", "S2=rules_unresolved"}
    assert "capture showing a state" in hz["label"] and hz["followup_slot_coverage"] is not None


def test_time_to_close_kaplan_meier(world):
    km = world["res"]["time_to_close"]["KM|all"]
    # final (5) and pending (2) units; the closed pending record (13) is an event, the open one (11) is censored at the fetch
    assert km["units"] == 7 and km["median_hours"]["est"] is not None
    assert 0.0 <= km["closed_by_7d"]["est"] <= 1.0 and km["closed_by_30d"]["est"] >= km["closed_by_7d"]["est"]
    assert world["res"]["wait_hours"]["n"] == 5
    assert "not_found" not in json.dumps(km) and set(world["res"]["time_to_close"]) >= {"KM|all", "KM|S1=low", "KM|S2=barrier"}


def test_post_k_classes_no_favourite_and_coverage(world):
    res = world["res"]
    pk = res["post_k_classes"]
    assert set(pk) == {"end_date_changed_after_k", "closed_before_t_d", "closed_within_one_slot"}
    assert pk["closed_before_t_d"]["units"] >= 0 and all("mean_n" in v for v in pk.values())
    nfv = res["no_favourite"]
    assert nfv["count"] == 1 and nfv["fetch_coverage"] == 1.0 and nfv["yes_resolved_share"] == 1.0 and "never in an estimand" in nfv["note"]
    cov = res["coverage"]
    assert cov["units"] == 1.0 and cov["events_all_units_covered"] == 1.0 and cov["floor"] == 0.95  # not_found and unavailable (other_price_vector) are definite answers
    assert res["backlog"]["not_found_plus_split_share"] == pytest.approx(2 / 9) and res["backlog"]["label"] is None
    assert res["m1_overlap"] == "unavailable"
    assert res["uma_status_by_class"]["pending"]
    assert res["rule25_reference_lines"]["tick_0.001"]["units"] > 0 and res["rule25_reference_lines"]["tick_0.01"]["reference_lines"] == {"mid_floor_cents": 0.5, "spread_floor_cents": 1.0}
    assert res["liquidity_proxy_not_capacity"]["mid"]["n"] > 0 and res["selection_width"] == {"splits": 12, "cells": 69, "contrasts": 2}


# --- refusals and void -------------------------------------------------------------------------------------------------------------------

def test_analysis_refusals(world, tmp_path):
    st, pins = world["st"], world["pins"]
    with pytest.raises(sp.M2Refusal, match="before READOUT_UTC"):
        an.run_analysis(st, pins, tmp_path / "o.json", SPEC, now=RO_T + 11 * 3600.0)
    with pytest.raises(sp.M2Refusal, match="--out"):
        an.run_analysis(st, pins, None, SPEC, now=RO_T + 13 * 3600.0)
    with pytest.raises(sp.M2Refusal, match="overwrite"):
        an.run_analysis(st, pins, world["out"], SPEC, now=RO_T + 13 * 3600.0)
    with pytest.raises(sp.PinMismatch):
        an.run_analysis(st, pins | {"code_sha": "0" * 64}, tmp_path / "o2.json", SPEC, now=RO_T + 13 * 3600.0)
    with pytest.raises(sp.PinMismatch):
        an.run_analysis(st, pins, tmp_path / "o3.json", SPEC, now=RO_T + 13 * 3600.0, design=tmp_path / "missing.md")
    with pytest.raises(sp.M2Refusal, match="registration_commit_utc"):
        an.run_analysis(st, {k: v for k, v in pins.items() if k != "registration_commit_utc"}, tmp_path / "o4.json", SPEC, now=RO_T + 13 * 3600.0)
    assert world["out"].exists() and json.loads(world["out"].read_text())["void"] is False


def test_void_when_the_manifest_hash_or_a_file_differs_or_the_followup_manifest_is_missing(world, tmp_path):
    st, pins = world["st"], world["pins"]
    r1 = an.run_analysis(st, pins | {"manifest_sha256": "0" * 64}, tmp_path / "v1.json", SPEC, now=RO_T + 13 * 3600.0)
    assert r1["void"] and any("11.7" in x and "differs from the pin" in x for x in r1["void_reasons"]) and "not_a_measurement" in r1 and "headline_ci" not in r1
    r2 = an.run_analysis(st, pins | {"followup_manifest_sha256": None}, tmp_path / "v2.json", SPEC, now=RO_T + 13 * 3600.0)
    assert r2["void"] and any("11.2(b)" in x for x in r2["void_reasons"]) and r2["not_a_measurement"]["proposal_hazard"].startswith("unavailable")
    r3 = an.run_analysis(st, pins | {"registration_commit_utc": "2026-10-20T00:00:00Z"}, tmp_path / "v3.json", SPEC, now=RO_T + 13 * 3600.0)
    assert r3["void"] and any("11.6" in x for x in r3["void_reasons"])


def test_void_when_the_followup_manifest_file_is_absent(tmp_path):
    snap, rr, st, man, fman, jm, pins = build_world(tmp_path)
    (st / "followup_manifest.json").unlink()
    r = an.run_analysis(st, pins, tmp_path / "o.json", SPEC, now=RO_T + 13 * 3600.0)
    assert r["void"] and any("followup_manifest.json missing" in x for x in r["void_reasons"])


def test_void_when_unit_lines_carry_other_pins_or_the_manifest_is_missing(tmp_path):
    snap, rr, st, man, fman, jm, pins = build_world(tmp_path)
    r = an.run_analysis(st, pins | {"code_sha": sp.code_sha(), "spec_sha": sp.spec_sha(SPEC)}, tmp_path / "ok.json", SPEC, now=RO_T + 13 * 3600.0)
    assert r["void"] is False
    (st / "manifest.json").unlink()
    r2 = an.run_analysis(st, pins, tmp_path / "nm.json", SPEC, now=RO_T + 13 * 3600.0)
    assert r2["void"] and any("manifest.json missing" in x for x in r2["void_reasons"]) and "headline_ci" not in r2


def test_void_below_the_coverage_floor_and_backlog_label(tmp_path):
    def break_fetch(db):
        for m in (1, 2, 5, 6, 14, 11, 13, 25):
            db.pop(m)  # every record absent in both passes: not_found for all (definite answers, so coverage holds) and a backlog label

    snap, rr, st, man, fman, jm, pins = build_world(tmp_path, mutate=break_fetch)
    r = an.run_analysis(st, pins, tmp_path / "o.json", SPEC, now=RO_T + 13 * 3600.0)
    assert r["classes"] == {"not_found": 9} and r["coverage"]["units"] == 1.0 and r["backlog"]["label"].startswith("the population behaves as the venue's backlog")
    assert r["final_units"] == 0 and r["void"] is False and r.get("note") == "no final-state units"


def test_coverage_floor_voids_when_the_fetch_leaves_units_unavailable(tmp_path):
    snap, rr = t1.build(tmp_path)
    st = tmp_path / "research_lab" / "m2_ch264"
    tc.run(snap, rr, st)
    man = cl.close_units(st, SPEC, now=sp.ts(SPEC, "end_utc") + 7 * 3600.0)
    fman = cl.close_followup(st, SPEC, now=RO_T + 60.0)
    clk = Clock(RO_T + 100.0)
    ro.run_j3(st, Gamma({m: rec(m) for m in (1, 2, 5, 6, 11, 12, 13, 14, 25, 4)}, fail={1, 2, 5, 6, 11, 12, 13, 14, 25, 4}), SPEC, now=RO_T + 100.0, sleep=clk.sleep, clock=clk)
    pins = {"spec_sha": sp.spec_sha(SPEC), "code_sha": sp.code_sha(), "registration_commit_utc": "2026-10-01T00:00:00Z", "manifest_sha256": man["manifest_sha256"], "followup_manifest_sha256": fman["manifest_sha256"]}
    r = an.run_analysis(st, pins, tmp_path / "o.json", SPEC, now=RO_T + 13 * 3600.0)
    assert r["void"] and any("11.4" in x for x in r["void_reasons"]) and r["coverage"]["units"] == 0.0 and "ledger_line" not in r


# --- estimand and bootstrap engine on synthetic unit lists ---------------------------------------------------------------------------------

def mk_unit(i, ev, side="YES", ask=0.8, state="resolved", y=1, cells=None, day=0, fee=0.01, closed_time="2026-10-21 03:00:00+00", closed=True):
    mid_f = round(ask - 0.01, 6)
    u = {"unit_id": f"m2:{i}", "market_id": i, "event_id": ev, "side": side, "ask_f": ask, "mid_f": mid_f, "half_spread": 0.01, "fee_l1": fee, "fee_l2": fee * 1.5, "rate_l2": 0.05, "exponent": 1.0,
         "t_d": 1.79e9, "k_start_utc": sp.iso(sp.ts(SPEC, "registered_utc") + day * 86400.0 + 3600.0), "end_date_k": 1.78e9, "liquidity": 100.0, "tick": "0.001", "cells": dict(cells or CELLS_OK)}
    r = {"market_id": i, "state": state, "y": y if state == "resolved" else None, "closed_time": closed_time, "fetched_utc": "2027-02-01T00:00:00Z", "uma": "resolved", "sub_class": None,
         "end_date": None}
    return u, r


def prep(specs, spec=SPEC):
    us, ro_ = [], {}
    for sp_ in specs:
        u, r = mk_unit(*sp_[0], **sp_[1])
        us.append(u)
        ro_[u["market_id"]] = r
    an.classify_units(us, ro_, spec)
    return us


def test_bootstrap_matrix_engine_equals_a_loop_reference_on_the_same_draws():
    spec = copy.deepcopy(SPEC)
    spec["bootstrap"] = {"B": 120, "seed": 20261125, "ci": 0.95, "chunk": 50}
    rng_u = np.random.default_rng(3)
    specs = []
    for i in range(60):
        specs.append(((i, f"e{i // 3}"), {"ask": float(rng_u.choice([0.6, 0.7, 0.8])), "y": int(rng_u.integers(0, 2)), "cells": CELLS_OK | {"S1": ["low", "mid", "high"][i % 3]}}))
    us = prep(specs, spec)
    bt = an.build_stats(us, spec)
    bt.run()
    events = sorted({u["event_id"] for u in us})
    E = len(events)
    rng = np.random.default_rng(spec["bootstrap"]["seed"])
    ref, done = [], 0
    while done < 120:
        m = min(50, 120 - done)
        idx = rng.integers(0, E, size=(m, E))
        for row in idx:
            chosen = [u for e in row for u in us if u["event_id"] == events[e]]
            fin = [u for u in chosen if u["final"]]
            ref.append(sum(u["n1"] for u in fin) / len(fin))
        done += m
    assert np.allclose(bt.draws["H|theta"], np.array(ref), atol=1e-12)
    lo, hi = np.percentile(ref, [2.5, 97.5])
    ci = bt.ci("H|theta")
    assert ci["lo"] == pytest.approx(lo) and ci["hi"] == pytest.approx(hi) and ci["draws_used"] == 120 and ci["draws_left_out"] == 0
    # a cell's CI uses the same draws restricted to its units; draws with no final-state unit in the cell are counted and left out
    small = prep([((1, "eX"), {"cells": CELLS_OK | {"S1": "low"}}), ((2, "eY"), {"cells": CELLS_OK | {"S1": "high"}, "state": "pending"}), ((3, "eZ"), {"cells": CELLS_OK | {"S1": "high"}, "state": "pending"}),
                  ((4, "eW"), {"cells": CELLS_OK | {"S1": "high"}})], spec)
    b2 = an.build_stats(small, spec)
    b2.run()
    c = b2.ci("S1|low|theta")
    assert c["draws_left_out"] > 0 and c["draws_used"] + c["draws_left_out"] == 120
    # reproducible, and the same seed gives the same draws
    b3 = an.build_stats(small, spec)
    b3.run()
    assert np.array_equal(np.nan_to_num(b2.draws["H|theta"]), np.nan_to_num(b3.draws["H|theta"]))


def test_degenerate_component_is_flagged_and_p_split_zero_gives_a_zero_interval():
    spec = copy.deepcopy(SPEC)
    spec["bootstrap"] = {"B": 100, "seed": 20261125, "ci": 0.95, "chunk": 50}
    us = prep([((i, f"e{i}"), {"y": 1}) for i in range(10)], spec)
    bt = an.build_stats(us, spec)
    bt.run()
    ci = bt.ci("H|p_split")
    assert ci["est"] == 0.0 and ci["lo"] == ci["hi"] == 0.0 and ci["degenerate"] is True


def test_each_class_enters_the_right_estimands():
    us = prep([((1, "a"), {"y": 1}), ((2, "b"), {"y": 0}), ((3, "c"), {"state": "split_50_50"}), ((4, "d"), {"state": "pending"}), ((5, "e"), {"state": "not_found"}),
               ((6, "f"), {"state": "unavailable_fetch"}), ((7, "g"), {"side": "NO", "y": 0}), ((8, "h"), {"side": "NO", "y": 1})])
    by = {u["market_id"]: u for u in us}
    assert [by[i]["cls"] for i in range(1, 9)] == ["resolved_favoured", "resolved_other", "split_50_50", "pending", "not_found", "unavailable_fetch", "resolved_favoured", "resolved_other"]
    assert [by[i]["Q"] for i in range(1, 9)] == [1.0, 0.0, 0.5, None, None, None, 1.0, 0.0]  # YES = outcome 0 (y = 1); NO = outcome 1 (y = 0)
    assert by[1]["n1"] == pytest.approx(1 - 0.8 - 0.01) and by[3]["n1"] == pytest.approx(0.5 - 0.8 - 0.01) and by[4]["n1"] is None
    assert by[5]["n_loss"] == pytest.approx(-0.8 - 0.01) and by[5]["n_win"] == pytest.approx(0.2 - 0.01)
    assert by[8]["n1"] == pytest.approx(-0.8 - 0.01)
    bt = an.build_stats(us, SPEC)
    bt.run()
    fin = [by[i]["n1"] for i in (1, 2, 3, 7, 8)]
    assert bt.point["H|theta"] == pytest.approx(sum(fin) / 5) and bt.point["H|theta_NF"] == pytest.approx((sum(fin) + by[5]["n_loss"]) / 6)
    assert bt.point["H|q_eff"] == pytest.approx((1 + 0 + 0.5 + 1 + 0) / 5)  # never valued at a midpoint: pending / unavailable are out of theta, not_found only in theta_NF


def test_pending_unavailable_and_event_clusters_in_ratio_stats_per_cell():
    us = prep([((1, "e1"), {"cells": CELLS_OK | {"S6": "(0.5,0.6]"}}), ((2, "e1"), {"cells": CELLS_OK | {"S6": "(0.5,0.6]"}, "y": 0}), ((3, "e2"), {"cells": CELLS_OK | {"S6": "(0.9,0.95]"}, "ask": 0.9})])
    bt = an.build_stats(us, SPEC)
    bt.run()
    assert bt.point["S6|(0.5,0.6]|theta"] == pytest.approx(((1 - 0.81) + (0 - 0.81)) / 2)
    assert bt.point["S6|(0.9,0.95]|theta"] == pytest.approx(1 - 0.9 - 0.01) and bt.point["S6|(0.7,0.8]|theta"] is None
    assert "S12|mid|barrier|theta" in bt.point and sum(1 for k in bt.point if k.startswith("S12|") and k.endswith("|theta")) == 24 + 0


def test_aalen_johansen_matches_a_reference_loop_and_censoring_rules():
    spec = copy.deepcopy(SPEC)
    spec["bootstrap"] = {"B": 20, "seed": 1, "ci": 0.95, "chunk": 20}
    us = prep([((i, f"e{i}"), {}) for i in range(8)], spec)
    T = np.array([1, 2, 2, 3, 5, 5, 400, 7])
    typ = np.array([2, 1, 1, 0, 1, 2, 1, 0])  # the unit with T = 400 is censored at 360 (an event past 30 d is not counted)
    bt = an.Boot(us, spec)
    bt.add_aj("g", T, typ, np.arange(8))
    bt.run()
    S, cp, cc = 1.0, 0.0, 0.0
    cif = {}
    for t in range(1, 361):
        n = int((np.minimum(T, 360) >= t).sum())
        dp = int(((T == t) & (typ == 1)).sum())
        dc = int(((T == t) & (typ == 2)).sum())
        if n:
            cp += S * dp / n
            cc += S * dc / n
            S *= 1 - (dp + dc) / n
        cif[t] = (cp, cc)
    r = bt.aj_res["g"]
    assert r["cif_P"]["6h"]["est"] == pytest.approx(cif[3][0]) and r["cif_C"]["6h"]["est"] == pytest.approx(cif[3][1])
    assert r["cif_P"]["30d"]["est"] == pytest.approx(cif[360][0]) and r["cif_P"]["24h"]["est"] == pytest.approx(cif[12][0])
    assert r["hazard_P_per_slot"]["2"]["est"] == pytest.approx(2 / 7) and r["hazard_P_per_slot"]["2"]["at_risk"] == 7


def test_followup_events_token_rule_competing_event_and_missing_intervals(tmp_path):
    snap = tmp_path / "research_lab" / "snapshots"
    for k in range(t1.N):
        m = t1.markets(k)
        if k == 11:
            m[1] = dict(m[1], uma='["proposed","disputed"]')  # whole token
        if k == 12:
            m[2] = dict(m[2], uma="unproposed_thing")  # a non-whitelist form with no whole token: descriptive, not P
            m[6] = dict(m[6], uma="resolvedish")
        if k == 13:
            m[11] = dict(m[11], uma="Resolved", closed="true")  # P and closed at the same capture: P wins
        t1.write_capture(snap, k, m)
    rr = tmp_path / "research_lab" / "stream_gamma_rules"
    t1.write_rules(rr)
    st = tmp_path / "research_lab" / "m2_ch264"
    tc.run(snap, rr, st)
    units = t1.read_units(st)
    evm, notes = an.followup_events(st, units, SPEC)
    assert evm["m2:1"] == (1, 1) and evm["m2:11"] == (3, 1) and evm["m2:2"][1] == 0 and evm["m2:6"][1] == 0
    assert notes["uma_other_followup"] >= 2


def test_kaplan_meier_median_and_shares_by_hand():
    spec = copy.deepcopy(SPEC)
    spec["bootstrap"] = {"B": 10, "seed": 1, "ci": 0.95, "chunk": 10}
    us = prep([((i, f"e{i}"), {}) for i in range(5)], spec)
    hours = np.array([10.0, 20.0, 20.0, 200.0, 900.0])
    ev = np.array([1.0, 1.0, 0.0, 1.0, 0.0])
    bt = an.Boot(us, spec)
    bt.add_km("k", np.arange(5), hours, ev)
    bt.run()
    # S(10) = 4/5; S(20) = 4/5 * (1 - 1/4) = 3/5; S(200) = 3/5 * (1 - 1/2) = 3/10 -> median 200 h; closed by 7 d (168 h) = 1 - 3/5; by 30 d (720 h) = 1 - 3/10
    r = bt.km_res["k"]
    assert r["median_hours"]["est"] == pytest.approx(200.0) and r["closed_by_7d"]["est"] == pytest.approx(0.4) and r["closed_by_30d"]["est"] == pytest.approx(0.7)


def test_post_k_classes_and_m1_overlap(tmp_path):
    us = prep([((1, "a"), {}), ((2, "b"), {}), ((3, "c"), {})])
    by = {u["market_id"]: u for u in us}
    by[1]["readout_end_date"] = "2027-03-01T00:00:00Z"  # moved after k
    by[2]["closed_time_ts"] = by[2]["t_d"] - 10.0  # closed before t_d
    by[3]["closed_time_ts"] = by[3]["t_d"] + 3600.0  # closed within one slot
    pk = an.post_k_classes(us)
    assert pk["end_date_changed_after_k"]["units"] == 1 and pk["closed_before_t_d"]["units"] == 1 and pk["closed_within_one_slot"]["units"] == 1
    assert all(u["final"] for u in us)  # no class removes a unit from any estimand
    m1 = tmp_path / "m1"
    (m1 / "units").mkdir(parents=True)
    with gzip.open(m1 / "units" / "x.jsonl.gz", "wt") as fh:
        fh.write(json.dumps({"market_id": 2, "capture_id": "c"}) + "\n" + json.dumps({"market_id": 99}) + "\n" + "not json\n")
    ov = an.m1_overlap(us, m1)
    assert ov["count"] == 1 and ov["m1_unit_markets_read"] == 2 and ov["m1_lines_missing_the_key"] == 1 and ov["pooled"] is False
    assert an.m1_overlap(us, tmp_path / "nowhere") == "unavailable"


def test_cross_check_compares_final_states_only():
    us = prep([((1, "a"), {"y": 1}), ((2, "b"), {"state": "pending"}), ((3, "c"), {"state": "split_50_50"})])
    log = {1: {"state": "resolved", "y": 1}, 2: {"state": "not_resolved"}, 3: {"state": "resolved", "y": 1}}
    cc = an.cross_check(us, log)
    assert cc["units_in_log"] == 3 and cc["disagree"] == 1 and cc["disagreements"][0]["market_id"] == 3 and "pinned source governs" in cc["note"]


def test_runner_analysis_refusals(world, tmp_path):
    import test_m2_code as tcm

    st = world["st"]
    r = tcm.runner
    assert r.main(["analysis", "--store", str(st)]) == 2  # no pins
    p = tmp_path / "pins.json"
    p.write_text(json.dumps(world["pins"]))
    assert r.main(["analysis", "--store", str(st), "--pins", str(p), "--out", str(tmp_path / "o.json")]) == 2  # the real clock is before READOUT_UTC + 12 h
    p.write_text(json.dumps(world["pins"] | {"code_sha": "0" * 64}))
    assert r.main(["j2", "--store", str(st), "--pins", str(p)]) == 3  # a pin mismatch exits 3 before any date check
    assert r.main(["j2", "--store", str(st)]) == 2  # real spec, real clock: before END_UTC + 6 h
    assert r.main(["j2", "--store", str(tmp_path / "research_lab" / "wrong_name")]) == 2
