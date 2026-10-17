# ruff: noqa: E501
"""CB5-L ladder-versus-bucket CDF consistency (astrolabe.research_lab.cb5_cdf)."""

from __future__ import annotations

import gzip
import json
import math
from datetime import date

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import cb5_cdf as c

ZERO_FEE = lambda d, cat, p: {"fee_rate": 0.0}  # noqa: E731
FEE = lambda d, cat, p: {"fee_rate": 0.05}  # noqa: E731
CREATED = "2026-05-01T00:00:00Z"
T0 = 1_785_000_000.0  # 2026-07


# ---- periods and tiling -------------------------------------------------------------------------------------------------


def test_parse_period_kinds_with_and_without_year():
    p = c.parse_period("June", CREATED)
    assert p["kind"] == "month" and p["start"] == date(2026, 6, 1) and p["end"] == date(2026, 6, 30)
    assert c.parse_period("January", CREATED)["start"] == date(2027, 1, 1)  # missing year: first such month on or after creation
    assert c.parse_period("February 2028", CREATED)["end"] == date(2028, 2, 29)
    q = c.parse_period("Q3", CREATED)
    assert q["kind"] == "quarter" and q["start"] == date(2026, 7, 1) and q["end"] == date(2026, 9, 30)
    assert c.parse_period("Q1 2027", CREATED)["start"] == date(2027, 1, 1)
    y = c.parse_period("2026", CREATED)
    assert y["kind"] == "year" and y["end"] == date(2026, 12, 31)
    o = c.parse_period("Before July", CREATED)
    assert o["kind"] == "open" and o["start"] is None and o["end"] == date(2026, 6, 30)
    assert c.parse_period("By June 30", CREATED)["end"] == date(2026, 6, 30)
    for t in ("Not in 2026", "After September", "2027 or later", "Never"):
        assert c.parse_period(t, CREATED)["kind"] == "close", t
    assert c.parse_period("Banana", CREATED) is None


def test_tiling_failure_on_gap_or_overlap():
    jun, jul, aug = (c.parse_period(x, CREATED) for x in ("June", "July", "August"))
    assert c.tiles([jun, jul, aug])
    assert not c.tiles([jun, aug])  # gap
    assert not c.tiles([jun, c.parse_period("Q2 2026", CREATED), jul])  # overlap
    assert c.tiles([c.parse_period("Before June", CREATED), jun, jul, c.parse_period("Never", CREATED)])


# ---- events, rungs, buckets --------------------------------------------------------------------------------------------


def market(i, title, question="", **kw):
    m = {"id": str(i), "conditionId": f"c{i}", "question": question, "groupItemTitle": title, "clobTokenIds": f'["a{i}","b{i}"]', "negRisk": False,
         "createdAt": CREATED, "endDate": "2026-12-31T00:00:00Z", "closed": False}
    m.update(kw)
    return m


def bucket_event(eid, titles=("June", "July", "August", "After August"), neg=True, augmented=False, title="When will the Acme merger be completed?", base=100, other=False, desc=""):
    ms = [market(base + k, t, negRisk=neg, negRiskOther=(other and k == 0)) for k, t in enumerate(titles)]
    return {"id": eid, "title": title, "negRisk": neg, "negRiskAugmented": augmented, "description": desc, "markets": ms}


def ladder_event(eid, deadlines, question="Will the Acme merger be completed by {d}?", base=200, desc=""):
    ms = [market(base + k, d, question.format(d=d)) for k, d in enumerate(deadlines)]
    return {"id": eid, "title": "Acme merger", "negRisk": False, "description": desc, "markets": ms}


def test_bucket_events_exclusions():
    ok = c.bucket_events([bucket_event("B1")])
    assert len(ok) == 1 and ok[0]["granularity"] == "month" and len(ok[0]["members"]) == 4
    assert not c.bucket_events([bucket_event("B2", augmented=True)])
    assert not c.bucket_events([bucket_event("B3", other=True)])
    assert not c.bucket_events([bucket_event("B4", titles=("June", "August", "After August"))])  # not tiling
    assert not c.bucket_events([bucket_event("B5", neg=False)])


def test_by_june_30_pairs_with_buckets_ending_on_or_before_and_before_july_is_same():
    b = c.bucket_events([bucket_event("B1")])
    lad = c.ladder_groups(c.ladder_rungs([ladder_event("L1", ["June 30", "July 31", "June 15"])]))
    fam = c.match_families(lad, b)
    assert len(fam) == 1
    ps = c.pairs(fam[0])
    assert {p["D"] for p in ps} == {date(2026, 6, 30), date(2026, 7, 31)}  # June 15 is inside a period: excluded
    assert c.off_boundary_rungs(fam[0]) == 1
    jun = next(p for p in ps if p["D"] == date(2026, 6, 30))
    assert jun["K"] == 1 and jun["B"] == ["100"]
    jul = next(p for p in ps if p["D"] == date(2026, 7, 31))
    assert jul["K"] == 2
    before = c.ladder_rungs([ladder_event("L2", ["July 1"], question="Will the Acme merger be completed before {d}?")])
    assert before[0]["D"] == date(2026, 6, 30)  # "before July 1" means by June 30


def test_dec_forms_and_no_deadline_word_excluded():
    ev = ladder_event("L3", ["June 30"], question="Will Acme continue through {d}?")
    assert not c.ladder_rungs([ev])
    ev = ladder_event("L4", ["June 30"], question="Will Acme exist on {d}?")
    assert not c.ladder_rungs([ev])


def test_conflict_numbers_and_source_rules():
    assert c.stems_match("will the acme president resign", "will the acme vice president resign") is None
    assert c.stems_match("will the acme merger be completed", "will the acme announce merger be completed") is None
    assert c.stems_match("will acme raise 5 million dollars", "will acme raise 6 million dollars") is None
    assert c.stems_match("will the acme merger be completed", "will the acme merger be completed") == 1.0
    assert c.sources_agree({"a.com"}, {"b.com"}) == (False, "source_mismatch")
    assert c.sources_agree({"a.com"}, {"a.com", "b.org"})[0]
    assert c.sources_agree(set(), set()) == (True, "source_unknown")
    assert not c.sources_agree({"a.com"}, set())[0]
    assert c.resolution_sources("Resolution source: https://www.sec.gov/filings and more") >= {"sec.gov"}


def test_mutual_best_margin_and_ties_dropped():
    lad = c.ladder_groups(c.ladder_rungs([ladder_event("L1", ["June 30"])]))
    two = c.bucket_events([bucket_event("B1"), bucket_event("B2", base=300)])  # identical stems: a tie within the margin
    assert c.match_families(lad, two) == []
    one = c.bucket_events([bucket_event("B1"), bucket_event("B9", base=400, title="When will the Zeta treaty be ratified?")])
    assert len(c.match_families(lad, one)) == 1
    mism = c.bucket_events([bucket_event("B1", desc="Resolution source: https://a.com")])
    lad2 = c.ladder_groups(c.ladder_rungs([ladder_event("L1", ["June 30"], desc="Resolution source: https://b.com")]))
    assert c.match_families(lad2, mism) == []


# ---- parse guard --------------------------------------------------------------------------------------------------------


def test_parse_guard_drops_outcome_fields(tmp_path):
    e = ladder_event("L1", ["June 30"])
    e["markets"][0]["outcomePrices"] = '["1","0"]'
    e["markets"][0]["outcomes"] = '["Yes","No"]'
    e["markets"][0]["umaResolutionStatus"] = "resolved"
    p = tmp_path / "events.jsonl.gz"
    with gzip.open(p, "wt") as fh:
        fh.write(json.dumps(e) + "\n")
    got = list(c.guarded_events(p))
    c.assert_no_outcomes(got)
    assert "outcomePrices" not in json.dumps(got) and "outcomes" not in got[0]["markets"][0]
    assert got[0]["markets"][0]["umaResolutionStatus"] == "resolved"  # kept only as a string


def test_walk_events_guards_every_record():
    class Lim:
        def get(self, url, params):
            return 200, [{"id": 1, "title": "x", "markets": [{"id": 1, "outcomePrices": "[1,0]", "question": "q"}]}]

    from datetime import UTC, datetime

    ev, rep = c.walk_events(datetime(2026, 10, 1, tzinfo=UTC), datetime(2026, 10, 8, tzinfo=UTC), Lim())
    c.assert_no_outcomes(ev)
    assert rep["windows"] == 1


# ---- pair state, payoff, execution --------------------------------------------------------------------------------------


def rows_frame(spec, t=T0, spread_s=0, **kw):
    """spec: {id: (bid, ask)}"""
    recs = []
    for k, (mid, (b, a)) in enumerate(spec.items()):
        recs.append({"market_id": mid, "best_bid": str(b), "best_ask": str(a), "volume_num": "100", "accepting_orders": "1", "closed": "False", "fee_category": "politics",
                     "received_utc": pd.Timestamp(t + k * spread_s, unit="s", tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ"), "sweep_ask_size_1": "10", "sweep_bid_size_1": "10", **kw})
    return pd.DataFrame(recs).set_index("market_id", drop=False)


PAIR = {"family_id": "F", "D": date(2026, 7, 31), "rung": "L", "B": ["b1", "b2"], "K": 2, "granularity": "month", "bucket_event": "BE"}


def test_net_arithmetic_and_payoff_in_every_state():
    r = rows_frame({"L": (0.60, 0.62), "b1": (0.20, 0.22), "b2": (0.25, 0.27)})
    st = c.pair_state(r, PAIR, date(2026, 7, 1), ZERO_FEE)
    assert st["eligible"]
    assert st["net_A"] == pytest.approx(0.60 - (0.22 + 0.27))  # bid(L) - sum ask(b)
    assert st["net_B"] == pytest.approx((0.20 + 0.25) - 0.62)  # sum bid(b) - ask(L)
    # payoff table: states = event in b1, event in b2, event after D (neither bucket, rung NO)
    for ly, by in (((1.0), [1.0, 0.0]), (1.0, [0.0, 1.0]), (0.0, [0.0, 0.0])):
        assert not c.payoff_short("A", 2, ly, by) and not c.payoff_short("B", 2, ly, by)
    # inconsistent states: bucket hit but rung NO (B comes up short), rung YES but no bucket hit (A comes up short)
    assert not c.payoff_short("A", 2, 0.0, [1.0, 0.0]) and c.payoff_short("B", 2, 0.0, [1.0, 0.0])
    assert c.payoff_short("A", 2, 1.0, [0.0, 0.0]) and not c.payoff_short("B", 2, 1.0, [0.0, 0.0])
    fees = c.pair_state(r, PAIR, date(2026, 7, 1), FEE)
    assert fees["net_A"] < st["net_A"] and fees["net_B"] < st["net_B"]


def test_leg_timing_rule_and_ineligible_legs():
    ok = rows_frame({"L": (0.6, 0.62), "b1": (0.2, 0.22), "b2": (0.25, 0.27)}, spread_s=100)
    assert c.leg_timing_ok(ok) and c.pair_state(ok, PAIR, date(2026, 7, 1), ZERO_FEE)["eligible"]
    slow = rows_frame({"L": (0.6, 0.62), "b1": (0.2, 0.22), "b2": (0.25, 0.27)}, spread_s=200)  # 400 s span
    assert not c.leg_timing_ok(slow)
    assert c.pair_state(slow, PAIR, date(2026, 7, 1), ZERO_FEE)["reason"] == "leg_timing"
    assert c.pair_state(ok.drop("b2"), PAIR, date(2026, 7, 1), ZERO_FEE)["reason"] == "leg_absent"
    one_sided = rows_frame({"L": (0.0, 0.62), "b1": (0.2, 0.22), "b2": (0.25, 0.27)})
    assert c.pair_state(one_sided, PAIR, date(2026, 7, 1), ZERO_FEE)["reason"] == "not_two_sided"
    closed = rows_frame({"L": (0.6, 0.62), "b1": (0.2, 0.22), "b2": (0.25, 0.27)}, closed="True")
    assert c.pair_state(closed, PAIR, date(2026, 7, 1), ZERO_FEE)["reason"] == "not_open"


def caps(rowsets, gaps_h):
    out, t = [], T0
    for i, rs in enumerate(rowsets):
        out.append({"capture_id": f"c{i}", "start_epoch": t, "rows": rs})
        t += gaps_h[i] * 3600.0 if i < len(gaps_h) else 7200.0
    return out


def test_trigger_executed_at_next_capture_gap_rule_and_ineligible_zero():
    rich = rows_frame({"L": (0.70, 0.72), "b1": (0.20, 0.22), "b2": (0.25, 0.27)})  # net_A = 0.70 - 0.49 = 0.21
    still = rows_frame({"L": (0.68, 0.70), "b1": (0.20, 0.22), "b2": (0.25, 0.27)})  # net_A' = 0.19
    gone = rows_frame({"L": (0.45, 0.47), "b1": (0.20, 0.22), "b2": (0.25, 0.27)})  # net_A' = -0.04 (kept, negative)
    u = c.triggers(caps([rich, still], [2]), [PAIR], ZERO_FEE)
    assert len(u) == 1 and u["exec_state"].iloc[0] == "executed" and u["net_exec"].iloc[0] == pytest.approx(0.19)
    u = c.triggers(caps([rich, gone], [2]), [PAIR], ZERO_FEE)
    assert u["net_exec"].iloc[0] == pytest.approx(-0.04)
    u = c.triggers(caps([rich, still], [4]), [PAIR], ZERO_FEE)  # gap outside [1.5, 3] h
    assert u["exec_state"].iloc[0] == "gap_out_of_range" and u["net_exec"].iloc[0] == 0.0
    bad = rows_frame({"L": (0.68, 0.70), "b1": (0.20, 0.22), "b2": (0.25, 0.27)}, spread_s=200)
    u = c.triggers(caps([rich, bad], [2]), [PAIR], ZERO_FEE)
    assert u["exec_state"].iloc[0].startswith("ineligible") and u["net_exec"].iloc[0] == 0.0
    quiet = rows_frame({"L": (0.49, 0.51), "b1": (0.20, 0.22), "b2": (0.25, 0.27)})
    assert len(c.triggers(caps([quiet, still], [2]), [PAIR], ZERO_FEE)) == 0  # below 0.5c: no trigger


# ---- coherence placebo (can fail) ---------------------------------------------------------------------------------------


def coherence_world(n_fam=25, coherent=True, seed=0, n_cap=6):
    rng = np.random.default_rng(seed)
    pairs, pool = [], []
    for i in range(n_fam):
        pairs.append({"family_id": f"F{i}", "D": date(2026, 6, 30), "rung": f"L{i}", "B": [f"B{i}_jun"], "K": 1, "granularity": "month", "bucket_event": f"B{i}"})
        pool.append({"event_id": f"B{i}", "granularity": "month", "members": [{"market_id": f"B{i}_jun", "end": date(2026, 6, 30), "kind": "month"},
                                                                              {"market_id": f"B{i}_jul", "end": date(2026, 7, 31), "kind": "month"}]})
    p = rng.uniform(0.15, 0.85, n_fam)
    out = []
    for k in range(n_cap):
        spec = {}
        for i in range(n_fam):
            pb = float(np.clip(p[i] + rng.normal(0, 0.004), 0.05, 0.93))
            pl = float(np.clip(pb + rng.normal(0, 0.004), 0.05, 0.93)) if coherent else float(rng.uniform(0.15, 0.85))
            spec[f"L{i}"] = (round(pl - 0.01, 4), round(pl + 0.01, 4))
            spec[f"B{i}_jun"] = (round(pb - 0.01, 4), round(pb + 0.01, 4))
            spec[f"B{i}_jul"] = (0.2, 0.22)
        out.append({"capture_id": f"c{k}", "start_epoch": T0 + 7200 * k, "rows": rows_frame(spec, t=T0 + 7200 * k)})
    return out, pairs, pool


def test_coherence_placebo_passes_when_matched_pairs_are_coherent():
    cp, pairs, pool = coherence_world(coherent=True)
    res = c.coherence_placebo(cp, pairs, pool, n_draws=40, regime=ZERO_FEE)
    assert res["testable"] and res["advance_ok"] and res["rate_as_coherent"] <= c.PLACEBO_MAX_ADVANCE_RATE


def test_coherence_placebo_fails_when_matched_pairs_no_more_coherent_than_unrelated():
    cp, pairs, pool = coherence_world(coherent=False, seed=4)
    res = c.coherence_placebo(cp, pairs, pool, n_draws=60, regime=ZERO_FEE)
    assert res["testable"] and not res["advance_ok"] and res["rate_as_coherent"] > c.PLACEBO_MAX_ADVANCE_RATE


def test_coherence_placebo_not_testable_below_20_families_and_only_same_granularity():
    cp, pairs, pool = coherence_world(n_fam=10)
    res = c.coherence_placebo(cp, pairs, pool, n_draws=5, regime=ZERO_FEE)
    assert not res["testable"] and not res["advance_ok"]
    quarter_pool = [{**b, "granularity": "quarter"} for b in pool]
    assert c.mismatch_pool(pairs[0], quarter_pool) == []
    assert all(b["event_id"] != "B0" for b in c.mismatch_pool(pairs[0], pool))  # never the matched event itself
    off_day = [{**b, "members": [{"market_id": "x", "end": date(2026, 6, 29), "kind": "month"}]} for b in pool]
    assert c.mismatch_pool(pairs[0], off_day) == []  # a boundary on the same day D is required


# ---- gates --------------------------------------------------------------------------------------------------------------


def test_wilson_and_r_inc_family_level_and_unknown_blocks():
    assert c.wilson_upper(0, 30) == pytest.approx(0.113, abs=0.001)
    assert c.wilson_upper(0, 61) == pytest.approx(0.0592, abs=0.001)
    fams = [{"family_id": f"F{i}", "pairs": [{"rung": f"L{i}", "B": [f"b{i}"]}]} for i in range(30)]
    out = {**{f"L{i}": 1.0 for i in range(30)}, **{f"b{i}": 1.0 for i in range(30)}}
    r = c.r_inc(fams, out)
    assert r["status"] == "known" and r["r_inc"] == 0.0 and r["r_inc_plus"] == pytest.approx(0.113, abs=0.001)
    unk = c.r_inc(fams[:29], out)
    assert unk["status"] == "unknown" and not c.divergence_gate(0.50, unk)["ok"]  # unknown blocks even a huge net
    assert not c.divergence_gate(0.05, r)["ok"] and c.divergence_gate(0.20, r)["ok"]
    bad = dict(out)
    bad["b3"] = 0.0  # rung YES but the bucket resolved NO: inconsistent
    rb = c.r_inc(fams, bad)
    assert rb["n_inconsistent_families"] == 1 and rb["pair_level"]["n_inconsistent"] == 1
    unresolved = dict(out)
    unresolved["b4"] = math.nan  # a family with an unresolved leg is not counted as resolved
    assert c.r_inc(fams, unresolved)["n_resolved_families"] == 29


def _units(n_fam, exec_sizes=True):
    rows = []
    for i in range(n_fam):
        rows.append({"family_id": f"F{i}", "direction": "A", "K": 1, "net": 0.02, "exec_state": "executed", "rung": f"L{i}", "B": [f"b{i}"],
                     "exec_ask_size": np.array([10.0, 10.0]) if exec_sizes else np.array([1.0, 1.0]), "exec_bid_size": np.array([10.0, 10.0])})
    return pd.DataFrame(rows)


def test_payoff_and_depth_gates_inconclusive_never_met():
    u = _units(10)
    out = {**{f"L{i}": 1.0 for i in range(10)}, **{f"b{i}": 1.0 for i in range(10)}}
    pg = c.realised_payoff_gate(u, out)
    assert pg["status"] == "inconclusive" and not pg["ok"]  # < 30 determined pairs
    big = _units(40)
    out = {**{f"L{i}": 1.0 for i in range(40)}, **{f"b{i}": 1.0 for i in range(40)}}
    assert c.realised_payoff_gate(big, out)["status"] == "pass"
    out2 = {**out, "b0": 0.0, "b1": 0.0, "b2": 0.0}
    assert c.realised_payoff_gate(big, out2)["status"] == "fail"
    dg = c.depth_check(_units(10))
    assert dg["status"] == "inconclusive" and not dg["ok"]
    assert c.depth_check(_units(40))["status"] == "pass"


def test_credit_status_pending_not_credited_and_stage1_blocks():
    good_pl = {"advance_ok": True}
    known = {"status": "known", "r_inc_plus": 0.02}
    div = {"ok": True}
    st2 = c.credit_status("stage2", advance_core=True, placebo=good_pl, rinc=known, divergence=div, payoff={"status": "inconclusive"}, depth={"status": "pass"})
    assert st2["passed"] and not st2["credited"] and "pending" in st2["family_status"]
    full = c.credit_status("stage2", advance_core=True, placebo=good_pl, rinc=known, divergence=div, payoff={"status": "pass"}, depth={"status": "pass"})
    assert full["credited"]
    s1 = c.credit_status("stage1", advance_core=True, placebo=good_pl, rinc={"status": "unknown"}, divergence={"ok": False}, payoff={}, depth={})
    assert not s1["advance"] and "r_inc_unknown" in s1["blockers"]
    s1b = c.credit_status("stage1", advance_core=True, placebo={"advance_ok": False, "testable": False}, rinc=known, divergence=div, payoff={}, depth={})
    assert not s1b["advance"]
    assert not c.g59_gate(19)["ok"] and c.g59_gate(20)["ok"]


def test_audit_allows_one_revision_and_raises_on_second():
    ok = c.apply_audit([True] * 48 + [False] * 2)
    assert ok["pass"] and ok["next"] == "freeze"
    first = c.apply_audit([True] * 46 + [False] * 4)
    assert not first["pass"] and first["next"] == "revise_once"
    with pytest.raises(c.GrouperAuditFailed):
        c.apply_audit([True] * 46 + [False] * 4, previous_failures=1)


def test_l1_test_and_helpers_and_families_doc():
    rng = np.random.default_rng(1)
    n = 150
    u = pd.DataFrame({"family_id": [f"F{i % 40}" for i in range(n)], "family_week": [f"F{i % 40}|2026-W{i % 3 + 30}" for i in range(n)], "net": rng.normal(0.02, 0.03, n),
                      "capital": np.ones(n), "hold_days": np.full(n, 30.0)})
    res = c.l1_test(u, n_boot=0)
    assert res["testable"] and res["p"] < 0.01 and res["r_ann"] > 0
    flat = u.assign(net=rng.normal(0.0, 0.03, n))
    assert c.l1_test(flat, n_boot=0)["p"] > 0.01
    assert not c.l1_test(u.head(20), n_boot=0)["testable"]
    b = c.bucket_events([bucket_event("B1")])
    lad = c.ladder_groups(c.ladder_rungs([ladder_event("L1", ["June 30"])]))
    fam = c.match_families(lad, b)
    doc = c.families_doc(fam, b, version=1, listed_utc={fam[0]["family_id"]: "2026-10-11T11:00:00Z", "P:B1": "2026-10-11T11:00:00Z"})
    from astrolabe.research_lab import cb5_extract as x

    assert doc["sha256"] == x.family_list_sha256(doc) and {e["role"] for e in doc["families"]} == {"family", "pool"}


def test_eligibility_counts_never_compute_a_gap():
    cp, pairs, pool = coherence_world(n_fam=3, n_cap=2)
    out = c.eligible_pair_captures(cp, pairs)
    assert out["n_families"] == 3 and out["n_pair_captures"] == 6 and not any("gap" in k for k in out)


def test_coherence_placebo_never_drops_a_pair_inside_a_draw(monkeypatch):
    """A pair whose every mismatch has no eligible series is excluded from BOTH sides up front (M_matched and every draw use the same pairs)."""
    cp, pairs, pool = coherence_world(n_fam=30, coherent=True)
    real = c.gap_mid_series

    def fake(captures, pair, regime):
        if pair["family_id"] == pairs[0]["family_id"] and pair["bucket_event"] != pairs[0]["bucket_event"]:
            return []  # every mismatch of the first family has no eligible capture
        return real(captures, pair, regime)

    monkeypatch.setattr(c, "gap_mid_series", fake)
    res = c.coherence_placebo(cp, pairs, pool, n_draws=20, regime=ZERO_FEE)
    assert res["n_pairs_excluded_no_mismatch"] >= 1
    assert res["n_pairs_used"] + res["n_pairs_excluded_no_mismatch"] == len({(p["family_id"], p["D"]) for p in pairs})
