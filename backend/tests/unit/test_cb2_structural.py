# ruff: noqa: E501
"""CB2 structural tests (L1/X1/X2 ladder dominance, P gate). Synthetic fixtures only; no network, no real data."""

from __future__ import annotations

import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import cb2_structural as cs
from astrolabe.research_lab import creative_batch1 as cb
from astrolabe.research_lab import provenance

H = 3600.0
DAY = 86400.0
T0 = cs._ep("2026-10-12T20:00:00Z")  # crosses a UTC midnight within a few captures
DL1 = cs._ep("2026-11-10T00:00:00Z")
DL2 = cs._ep("2026-12-10T00:00:00Z")

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))


def iso(t: float) -> str:
    return datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------------------------
# parse_direction / grouper
# ---------------------------------------------------------------------------------------------

CREATED = "2026-10-01T00:00:00Z"


@pytest.mark.parametrize("q,direction", [
    ("Will X be released by October 31, 2026?", "INC"),
    ("Will Y happen before March 5?", "INC"),
    ("Will the ceasefire continue through December 31?", "DEC"),
    ("Will the ceasefire continues through December 31, 2026?", "DEC"),
    ("Will the shutdown last until November 30?", "DEC"),
    ("Will X happen on October 31?", None),
    ("Will X happen in October?", None),
    ("Will X happen by October?", None),
    ("Will X happen between October 1 and October 5?", None),
    ("Will X happen?", None),
])
def test_parse_direction(q, direction):
    assert cs.parse_direction(q, CREATED)["direction"] == direction


def test_parse_direction_survival_and_point_date_pairs_never_form_violations():
    """Section 0.1 fixtures: survival ladders are DEC (falling with D is correct), point-date ('on D') markets are excluded."""
    mk = [{"market_id": "1", "event_id": "E1", "question": "Will the ceasefire continue through October 31?", "description": "d", "created_at": CREATED},
          {"market_id": "2", "event_id": "E1", "question": "Will the ceasefire continue through November 30?", "description": "d", "created_at": CREATED},
          {"market_id": "3", "event_id": "E2", "question": "Will the strike happen on October 20?", "description": "d", "created_at": CREATED},
          {"market_id": "4", "event_id": "E2", "question": "Will the strike happen on October 21?", "description": "d", "created_at": CREATED}]
    g = cs.ladder_grouper_v2(mk)
    assert [(L["direction"], L["type"]) for L in g["ladders"]] == [("DEC", "L")]
    assert g["counts"]["excluded_point_or_period_on"] == 2
    p = cs.ladder_pairs(cs.ladder_list(g, version=1, listed_utc="2026-10-16T01:00:00Z"))
    r = p.iloc[0]
    assert r["yes_m"] == "1" and r["no_m"] == "2"  # DEC: YES earlier, NO later


def _mk(mid, ev, q, desc="resolves per source A on date 2026-10-01"):
    return {"market_id": mid, "event_id": ev, "question": q, "description": desc, "created_at": CREATED}


def test_within_ladder_dedupes_deadline_keeps_lowest_id():
    g = cs.ladder_grouper_v2([_mk("20", "E", "Will X happen by October 31?"), _mk("10", "E", "Will X happen by October 31?"),
                              _mk("30", "E", "Will X happen by November 30?")])
    assert g["counts"]["dup_deadline_dropped"] == 1
    assert [r["market_id"] for r in g["ladders"][0]["rungs"]] == ["10", "30"]


def test_cross_event_grouping_requires_equal_masked_descriptions():
    q1, q2 = "Will the central bank cut rates by October 31?", "Will the central bank cut rates by November 30?"
    d_same_a = "Resolves YES if the central bank cuts rates by October 31, 2026. Source: official site."
    d_same_b = "Resolves YES if the central bank cuts rates by November 30, 2026. Source: official site."
    g = cs.ladder_grouper_v2([_mk("1", "E1", q1, d_same_a), _mk("2", "E2", q2, d_same_b)])
    assert [L["type"] for L in g["ladders"]] == ["X"]
    other = "Resolves YES per a different source: press reports only."
    g2 = cs.ladder_grouper_v2([_mk("1", "E1", q1, d_same_a), _mk("2", "E2", q2, other)])
    assert g2["ladders"] == []
    g3 = cs.ladder_grouper_v2([_mk("1", "E1", q1, ""), _mk("2", "E2", q2, "")])
    assert g3["ladders"] == [] and g3["counts"]["cross_empty_description"] == 1
    # short stems never group across events
    g4 = cs.ladder_grouper_v2([_mk("1", "E1", "Will X by October 31?"), _mk("2", "E2", "Will X by November 30?")])
    assert g4["ladders"] == [] and g4["counts"]["cross_short_stem"] == 1


def test_cross_event_with_several_rungs_in_one_event_is_excluded_and_counted():
    d = "same resolution text"
    q = "Will the central bank cut rates by {}?"
    g = cs.ladder_grouper_v2([_mk("1", "E1", q.format("October 31"), d), _mk("2", "E1", q.format("November 30"), d),
                              _mk("3", "E2", q.format("December 31"), d)])
    assert [L["type"] for L in g["ladders"]] == ["L"]  # E1 forms a within ladder; X would need >= 2 single-rung events
    assert g["counts"]["cross_event_multi_rung"] == 1


# ---------------------------------------------------------------------------------------------
# grouper seal, declaration, versioned list
# ---------------------------------------------------------------------------------------------


def test_grouper_hash_matches_committed_file_and_is_enforced(tmp_path):
    assert cs.require_grouper_seal() == cs.GROUPER_RULE_SHA256  # the real committed seal
    bad = tmp_path / "seal.json"
    bad.write_text(json.dumps({"sha256": "0" * 64}))
    with pytest.raises(cs.GrouperRuleError):
        cs.require_grouper_seal(bad)
    with pytest.raises(cs.GrouperRuleError):
        cs.require_grouper_seal(tmp_path / "absent.json")


def test_grouper_hash_covers_the_regexes(monkeypatch):
    h0 = cs.grouper_rule_sha256()
    monkeypatch.setitem(cs.GROUPER_RULES["words"], "inc", ["by"])
    assert cs.grouper_rule_sha256() != h0


def test_declaration_guard(tmp_path):
    spec = tmp_path / "cb2_v1.json"
    with pytest.raises(cs.DeclarationError):
        cs.require_declaration(spec)
    spec.write_text(json.dumps({"structural_sha256": "x"}))
    with pytest.raises(cs.DeclarationError):
        cs.require_declaration(spec)
    spec.write_text(json.dumps({"structural_sha256": cs.declaration_sha256_structural()}))
    assert cs.require_declaration(spec) == cs.declaration_sha256_structural()


def _grouped(ladders):
    return {"ladders": ladders, "counts": {}}


def _ladder(lid, typ, direction, rungs):
    return {"ladder_id": lid, "type": typ, "direction": direction, "stem": "s", "event_ids": sorted({r[1] for r in rungs}),
            "rungs": [{"market_id": r[0], "event_id": r[1], "deadline": r[2], "question": f"q{r[0]}"} for r in rungs]}


def test_ladder_list_version_rule_and_sha(tmp_path):
    v1 = cs.ladder_list(_grouped([_ladder("L:E:a", "L", "INC", [("1", "E", DL1), ("2", "E", DL2)])]), version=1,
                        listed_utc="2026-10-16T01:00:00Z")
    assert v1["rungs"][0]["visible_from_utc"] == cs.T2_DEV_START and not v1["rungs"][0]["strict"]
    assert cs._content_sha(v1) == v1["sha256"]
    v2 = cs.ladder_list(_grouped([_ladder("L:E:a", "L", "INC", [("1", "E", DL1), ("2", "E", DL2), ("3", "E", DL1 + 5 * DAY)]),
                                  _ladder("L:F:b", "L", "INC", [("7", "F", DL1), ("8", "F", DL2)])]),
                        version=2, listed_utc="2026-10-23T01:00:00Z", prev=v1)
    byid = {r["market_id"]: r for L in v2["ladders"] for r in L["rungs"]}
    assert byid["1"]["added_version"] == 1 and byid["3"]["added_version"] == 2 and byid["3"]["strict"]
    # a rung added by v2 is absent before that version's listed_utc and for a capture exactly at it; v1 rungs always visible
    assert not cs.rung_visible(byid["3"], cs._ep("2026-10-23T01:00:00Z"))
    assert not cs.rung_visible(byid["3"], cs._ep("2026-10-22T12:00:00Z"))
    assert cs.rung_visible(byid["3"], cs._ep("2026-10-23T03:00:00Z"))
    assert cs.rung_visible(byid["1"], cs._ep(cs.T2_DEV_START))
    assert cs.rung_visible(byid["1"], cs._ep("2026-10-11T12:00:00Z")) and not cs.rung_visible(byid["1"], cs._ep("2026-10-11T11:59:59Z"))
    # v1 data in the doc are untouched
    assert [r["market_id"] for r in v2["ladders"][0]["rungs"]] == ["1", "3", "2"] and v2["ladders"][0]["rungs"][0] == v1["ladders"][0]["rungs"][0]
    with pytest.raises(cs.LadderListError):
        cs.ladder_list(_grouped([]), version=3, listed_utc="2026-10-30T00:00:00Z", prev=v1)
    cs.write_ladder_list(v1, tmp_path)
    with pytest.raises(cs.LadderListError):
        cs.write_ladder_list(v1, tmp_path)
    assert (tmp_path / "ladder_list.json.sha256").read_text().strip() == v1["sha256"]
    assert cs.load_ladder_list(tmp_path / "ladder_list.json", v1["sha256"])["sha256"] == v1["sha256"]


def test_pairs_use_epoch_adjacency():
    v1 = cs.ladder_list(_grouped([_ladder("L:E:a", "L", "INC", [("1", "E", DL1), ("2", "E", DL2)])]), version=1, listed_utc="2026-10-16T01:00:00Z")
    v2 = cs.ladder_list(_grouped([_ladder("L:E:a", "L", "INC", [("1", "E", DL1), ("2", "E", DL2), ("3", "E", DL1 + 5 * DAY)])]),
                        version=2, listed_utc="2026-10-23T01:00:00Z", prev=v1)
    p = cs.ladder_pairs(v2)
    e1 = p[p["epoch"] == 1]
    e2 = p[p["epoch"] == 2]
    assert [(r.m1, r.m2) for r in e1.itertuples()] == [("1", "2")]
    assert sorted((r.m1, r.m2) for r in e2.itertuples()) == [("1", "3"), ("3", "2")]
    assert math.isinf(e2.iloc[0]["t_hi"]) and e1.iloc[0]["t_hi"] == cs._ep("2026-10-23T01:00:00Z")


def test_audit_sample_random_per_type_plus_extra():
    ladders = [_ladder(f"L:E{i}:a", "L", "INC", [(str(10 * i + 1), f"E{i}", DL1), (str(10 * i + 2), f"E{i}", DL2)]) for i in range(80)]
    ladders += [_ladder("X:INC:z", "X", "INC", [("901", "A", DL1), ("902", "B", DL2)])]
    doc = cs.ladder_list(_grouped(ladders), version=1, listed_utc="2026-10-16T01:00:00Z")
    a = cs.audit_sample(doc, extra_pair_ids=["L:E3:a|31|32"])
    assert sum(1 for r in a["pairs"] if r["source"] == "random" and r["type"] == "L") == 50
    assert sum(1 for r in a["pairs"] if r["type"] == "X") == 1
    assert any(r["source"] == "gap_ge_20c" or r["pair_id"] == "L:E3:a|31|32" for r in a["pairs"])
    assert a == cs.audit_sample(doc, extra_pair_ids=["L:E3:a|31|32"])  # deterministic
    assert cs.audit_verdict({f"p{i}": i >= 5 for i in range(100)})["pass"]
    assert not cs.audit_verdict({f"p{i}": i >= 6 for i in range(100)})["pass"]


# ---------------------------------------------------------------------------------------------
# pair payoffs, fees, next-capture execution
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("direction", ["INC", "DEC"])
def test_pair_payoffs_at_least_one_in_every_consistent_state(direction):
    # INC: event by D1 => by D2 (y1 <= y2). DEC: survive through D2 => through D1 (y2 <= y1).
    states = [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0)] if direction == "INC" else [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)]
    pays = [cs.pair_payoff(direction, y1, y2) for y1, y2 in states]
    assert all(p >= 1.0 for p in pays) and max(pays) == 2.0
    bad = (1.0, 0.0) if direction == "INC" else (0.0, 1.0)
    assert cs.pair_payoff(direction, *bad) == 0.0  # inconsistent resolution: CH13's named risk
    assert cs.realised_pair_payoff(direction, *bad)[2] is True
    assert cs.realised_pair_payoff(direction, *states[0])[2] is False


def test_realised_payoff_bounds_with_unknown_rungs():
    # INC, earlier rung resolved NO => NO leg pays 1 => payoff >= 1 whatever the later rung does
    assert cs.realised_pair_payoff("INC", 0.0, math.nan)[2] is False
    # INC, earlier YES, later unknown: payoff in [0, 1]: undetermined
    assert cs.realised_pair_payoff("INC", 1.0, math.nan)[2] is None
    assert cs.realised_pair_payoff("INC", math.nan, math.nan)[2] is None


CARD = ["capture_id", "capture_start_utc", "received_utc", "market_id", "event_id", "best_bid", "best_ask", "last_trade_price", "closed",
        "active", "accepting_orders", "end_date", "volume_num", "fee_schedule", "fee_category", "sw1_best_bid", "sw1_best_ask",
        "sw1_bid_size_1", "sw1_ask_size_1"]


def crow(cid, t, mid, ev, bid, ask, *, cat="geopolitics", **kw):
    r = {"capture_id": cid, "capture_start_utc": iso(t), "received_utc": iso(t + 60), "market_id": mid, "event_id": ev, "best_bid": bid,
         "best_ask": ask, "last_trade_price": (bid + ask) / 2, "closed": "False", "active": "True", "accepting_orders": 1.0,
         "end_date": iso(DL2), "volume_num": 100.0, "fee_schedule": "", "fee_category": cat, "sw1_best_bid": np.nan,
         "sw1_best_ask": np.nan, "sw1_bid_size_1": np.nan, "sw1_ask_size_1": np.nan}
    r.update(kw)
    return r


def inc_doc(n_l=0, n_x=0):
    """n_l within INC ladders (rungs A earlier, B later) and n_x cross INC ladders (events differ)."""
    ladders = []
    for i in range(n_l):
        ladders.append(_ladder(f"L:E{i}:a", "L", "INC", [(f"a{i}", f"E{i}", DL1), (f"b{i}", f"E{i}", DL2)]))
    for i in range(n_x):
        ladders.append(_ladder(f"X:INC:{i}", "X", "INC", [(f"xa{i}", f"XA{i}", DL1), (f"xb{i}", f"XB{i}", DL2)]))
    return cs.ladder_list(_grouped(ladders), version=1, listed_utc="2026-10-16T01:00:00Z")


def _pairs_for(doc):
    return cs.ladder_pairs(doc)


def test_next_capture_execution_gap_filter_and_closed_rung(tmp_path):
    doc = inc_doc(n_l=1)
    # captures 2h apart, then a 10h outage, then one more
    ts = [T0, T0 + 2 * H, T0 + 12 * H]
    rows = []
    for k, t in enumerate(ts):
        cid = f"c{k}"
        rows += [crow(cid, t, "a0", "E0", 0.55, 0.57), crow(cid, t, "b0", "E0", 0.40, 0.45)]  # violation: bid(A)=.55 > ask(B)=.45
    cands = pd.DataFrame(rows)
    cands["cs"] = cands["capture_start_utc"].map(cs._ep)
    ps, _ = cs.pair_states(cands, _pairs_for(doc))
    assert len(ps) == 3 and ps["viol"].all()
    nxt, gc = cs.c1.next_capture_pairs({"c0": ts[0], "c1": ts[1], "c2": ts[2]}, cs.GAP_H)
    assert nxt == {"c0": "c1"} and gc["excluded_gap"] == 1  # 10h outage pair dropped
    trig, cnt = cs.lx_triggers(ps, nxt)
    assert cnt["triggers"] == 1 and cnt["no_next_or_gap"] == 2 and cnt["executed"] == 1
    r = trig.iloc[0]
    # YES on B at ask .45 and NO on A at 1 - .55 = .45 (zero-fee category): C = 0.90, net = 0.10
    assert r["C0"] == pytest.approx(0.90) and r["net"] == pytest.approx(0.10) and r["exec_capture_id"] == "c1"
    # a rung that is closed at c' gives no trade (net 0, kept)
    cands2 = cands.copy()
    cands2.loc[(cands2["capture_id"] == "c1") & (cands2["market_id"] == "b0"), "closed"] = "True"
    ps2, _ = cs.pair_states(cands2, _pairs_for(doc))
    trig2, cnt2 = cs.lx_triggers(ps2, nxt)
    assert cnt2["no_trade"] == 1 and trig2.iloc[0]["net"] == 0.0 and not trig2.iloc[0]["executed"]


def test_cost_sums_fees_per_leg_with_each_legs_own_category():
    doc = inc_doc(n_l=1)
    cands = pd.DataFrame([crow("c0", T0, "a0", "E0", 0.55, 0.57, cat="crypto"), crow("c0", T0, "b0", "E0", 0.40, 0.45, cat="geopolitics")])
    cands["cs"] = T0
    ps, _ = cs.pair_states(cands, _pairs_for(doc))
    fee_no = 0.0  # NO leg is on A (crypto, 7%)
    a_n = 1 - 0.55
    fee_no = round(0.07 * (a_n * (1 - a_n)), 5)
    assert ps.iloc[0]["C"] == pytest.approx(0.45 + 0.0 + a_n + fee_no, abs=1e-4)


def test_pair_state_eligibility_fails_closed_on_unknown_flags():
    doc = inc_doc(n_l=1)
    base = [crow("c0", T0, "a0", "E0", 0.55, 0.57), crow("c0", T0, "b0", "E0", 0.40, 0.45)]
    for mut in ({"accepting_orders": np.nan}, {"closed": "unknown"}, {"volume_num": 0.0}, {"volume_num": np.nan}, {"best_ask": 1.0}):
        rows = [dict(base[0]), dict(base[1])]
        rows[1].update(mut)
        cands = pd.DataFrame(rows)
        cands["cs"] = T0
        ps, _ = cs.pair_states(cands, _pairs_for(doc))
        assert len(ps) == 0, mut


def test_visibility_in_pair_states_uses_the_list_version_rule():
    v1 = cs.ladder_list(_grouped([_ladder("L:E:a", "L", "INC", [("1", "E", DL1), ("2", "E", DL2)])]), version=1, listed_utc="2026-10-12T00:00:00Z")
    v2 = cs.ladder_list(_grouped([_ladder("L:E:a", "L", "INC", [("1", "E", DL1), ("2", "E", DL2), ("3", "E", DL1 + 5 * DAY)])]),
                        version=2, listed_utc="2026-10-13T00:00:00Z", prev=v1)
    ts = [cs._ep("2026-10-12T22:00:00Z"), cs._ep("2026-10-13T02:00:00Z")]
    rows = []
    for k, t in enumerate(ts):
        for mid, bid, ask in (("1", 0.50, 0.52), ("2", 0.30, 0.35), ("3", 0.40, 0.42)):
            rows.append(crow(f"c{k}", t, mid, "E", bid, ask))
    cands = pd.DataFrame(rows)
    cands["cs"] = cands["capture_start_utc"].map(cs._ep)
    ps, _ = cs.pair_states(cands, cs.ladder_pairs(v2))
    seen = {(r.capture_id, r.pair_id.split("|", 1)[1]) for r in ps.itertuples()}
    assert seen == {("c0", "1|2"), ("c1", "1|3"), ("c1", "3|2")}  # rung 3 absent from the capture before v2's listed_utc


# ---------------------------------------------------------------------------------------------
# end-to-end L1 / X1 / X2 on synthetic extract
# ---------------------------------------------------------------------------------------------


def build_extract(root: Path, n_l=40, n_x=40, n_cap=6, window="dev", viol_l=1.0, viol_x=0.5, seed=1):
    rng = np.random.default_rng(seed)
    doc = inc_doc(n_l=n_l, n_x=n_x)
    tbl = cs.table_for_window(window)
    (root / tbl).mkdir(parents=True, exist_ok=True)
    (root / "capture_lists").mkdir(exist_ok=True)
    man = {"captures": {}}
    ids = []
    t_start = T0 if window == "dev" else cs._ep(cs.load_pinned_rep_start()["t2_rep_start"]) + 3600
    for k in range(n_cap):
        t = t_start + k * 2 * H
        cid = f"c{k}"
        ids.append(cid)
        man["captures"][cid] = {"started_utc": iso(t), tbl: {"status": "written"}}
        rows = []
        for i in range(n_l):
            v = rng.random() < viol_l
            rows += [crow(cid, t, f"a{i}", f"E{i}", 0.55 + 0.003 * (i % 5) if v else 0.20, 0.57 + 0.003 * (i % 5) if v else 0.22),
                     crow(cid, t, f"b{i}", f"E{i}", 0.40, 0.45)]
        for i in range(n_x):
            v = rng.random() < viol_x
            rows += [crow(cid, t, f"xa{i}", f"XA{i}", 0.55 if v else 0.20, 0.57 if v else 0.22), crow(cid, t, f"xb{i}", f"XB{i}", 0.40, 0.45)]
        pd.DataFrame(rows).to_csv(root / tbl / f"{cid}.csv.gz", index=False)
    (root / "manifest.json").write_text(json.dumps(man))
    return doc, ids


def freeze(root, ids, window="dev"):
    lo, hi = cs.window_bounds(window)
    sha = cb.ids_sha256(ids)
    (root / "capture_lists" / f"cb2_{window}.json").write_text(json.dumps({
        "kind": f"cb2_{window}", "from_utc": iso(lo), "until": iso(hi), "capture_ids": ids, "sha256": sha, "final": True,
        "missing_ids": []}))
    return sha


def test_run_lx_dev_end_to_end(tmp_path):
    doc, ids = build_extract(tmp_path)
    sha = freeze(tmp_path, ids)
    cl = cs.load_cb2_list(tmp_path, "dev", sha)
    res, built = cs.run_lx(tmp_path, cl, doc, "dev", n_boot=200, n_perm=200, placebo_draws=20)
    l1 = res["tests"]["L1"]
    assert l1["testable"] and l1["n_event"] == 40 and l1["n"] >= 100
    assert l1["mean"] == pytest.approx(0.09, abs=0.02)
    assert l1["advance"] is True  # structural carry of ~9c per pair with R_ann >> 10%, all LODO > 0
    assert res["gates"]["L1"]["depth"]["status"].startswith("inconclusive")  # no sweeps
    assert set(res["tests"]) == {"L1", "X1", "X2"}
    assert res["persistence_diagnostic"]["L"]["is_null"] is False
    # no outcome column is read anywhere in the dev path
    assert not any("outcome" in c or "final" in c for c in built["ps"].columns)
    # X2: cross ladders violate half as often as within ladders: Delta < 0, no advance
    x2 = res["tests"]["X2"]
    assert x2["testable"] and x2["mean"] < 0 and x2["advance"] is False


def test_depth_gate_fail_blocks_dev_advance(tmp_path):
    doc, ids = build_extract(tmp_path, n_x=0)
    for cid in ids:  # swept legs whose ask is far worse: sweep net negative
        p = tmp_path / "ladder_candidates" / f"{cid}.csv.gz"
        d = pd.read_csv(p, dtype={"market_id": str, "event_id": str})
        a, b = d["market_id"].str.startswith("a"), d["market_id"].str.startswith("b")
        d.loc[b, ["sw1_best_ask", "sw1_ask_size_1"]] = [0.80, 50.0]
        d.loc[a, ["sw1_best_bid", "sw1_bid_size_1"]] = [0.20, 50.0]
        d.to_csv(p, index=False)
    sha = freeze(tmp_path, ids)
    res, _ = cs.run_lx(tmp_path, cs.load_cb2_list(tmp_path, "dev", sha), doc, "dev", n_boot=100, tests=("L1",))
    assert res["gates"]["L1"]["depth"]["status"] == "fail"
    assert res["tests"]["L1"]["advance"] is False


def test_x2_indicator_has_no_fee_term_and_one_value_per_ladder(tmp_path):
    doc, ids = build_extract(tmp_path, n_l=3, n_x=3, viol_l=1.0, viol_x=1.0, n_cap=4)
    cl = cs.load_cb2_list(tmp_path, "dev", freeze(tmp_path, ids))
    b = cs.build_lx(tmp_path, cl, doc, "dev")
    ps = b["ps"]
    # gap = bid(NO side rung A) - ask(YES side rung B) > 0 regardless of the fee category: switch to crypto and compare
    d = pd.read_csv(tmp_path / "ladder_candidates" / "c0.csv.gz", dtype={"market_id": str, "event_id": str})
    d["fee_category"] = "crypto"
    d.to_csv(tmp_path / "ladder_candidates" / "c0.csv.gz", index=False)
    ps2 = cs.build_lx(tmp_path, cl, doc, "dev")["ps"]
    assert ps2["viol"].tolist() == ps["viol"].tolist() and ps2["C"].sum() > ps["C"].sum()
    u = cs.ladder_rates(ps)
    assert len(u) == 6 and u["ladder_id"].is_unique


def _units(rows):
    return pd.DataFrame(rows, columns=["ladder_id", "ltype", "v", "n_pc", "stratum"])


def test_x2_estimator_strata_dropped_and_permutation_stays_within_strata():
    rng = np.random.default_rng(3)
    rows = []
    for i in range(40):  # stratum 'a': cross high, within low
        rows.append((f"X{i}", "X", 0.5 + 0.1 * rng.random(), 5, "a"))
        rows.append((f"L{i}", "L", 0.1 + 0.1 * rng.random(), 5, "a"))
    for i in range(10):  # stratum 'b': cross AND within both low; 'c': within only (dropped)
        rows.append((f"Xb{i}", "X", 0.1, 5, "b"))
        rows.append((f"Lb{i}", "L", 0.1, 5, "b"))
    rows += [(f"Lc{i}", "L", 0.9, 5, "c") for i in range(5)]
    u = _units(rows)
    est = cs.x2_estimate(u, perm_draws=300)
    assert est["testable"] and est["n_strata"] == 2 and est["strata_dropped"] == 1 and est["ladders_dropped"] == 5
    w_a, w_b = 40 / 50, 10 / 50
    assert est["mean"] == pytest.approx(w_a * (u[(u.stratum == "a") & (u.ltype == "X")].v.mean() - u[(u.stratum == "a") & (u.ltype == "L")].v.mean())
                                         + w_b * 0.0)
    assert est["p"] < 0.01 and est["p_perm"] >= 1 / 301 and est["p"] == max(est["p_z"], est["p_perm"])
    # a pure-composition difference (cross ladders sit only in the high-v stratum) is NOT a difference within strata
    rows2 = [(f"X{i}", "X", 0.8, 5, "hi") for i in range(5)] + [(f"L{i}", "L", 0.8, 5, "hi") for i in range(5)]
    rows2 += [(f"X2{i}", "X", 0.1, 5, "lo") for i in range(60)] + [(f"L2{i}", "L", 0.1, 5, "lo") for i in range(60)]
    e2 = cs.x2_estimate(_units(rows2), perm_draws=100)
    assert e2["mean"] == pytest.approx(0.0, abs=1e-12)
    # not testable under 30 per type
    assert cs.x2_estimate(_units(rows[:20] + [(f"Lz{i}", "L", 0.2, 5, "a") for i in range(3)]), perm_draws=50)["testable"] is False


def test_x2_placebo_is_calibrated_under_the_null():
    rng = np.random.default_rng(4)
    rows = []
    for s in ("a", "b", "c"):
        for i in range(50):
            rows.append((f"X{s}{i}", "X", float(rng.random() * 0.2), 5, s))
            rows.append((f"L{s}{i}", "L", float(rng.random() * 0.2), 5, s))
    pl = cs.x2_placebo(_units(rows), floor=0.01, alpha=0.01, draws=200)
    assert pl["draws"] == 200 and pl["advance_rate"] <= 0.03


def test_ladder_candidates_are_text_free_and_need_no_ladder_list():
    assert not any(c in cb.LADDER_COLUMNS for c in ("question", "description", "slug", "title", "group_item_title"))
    ent = {}
    cap = {"capture_id": "c", "_start": pd.Timestamp("2026-10-12T00:00:00Z").to_pydatetime()}
    assert cb._cb2_needs(cap, ent, ("ladder_candidates",), set(), None) == {"ladder_candidates"}


# ---------------------------------------------------------------------------------------------
# P gate: placeholder definition, no outcomes
# ---------------------------------------------------------------------------------------------


def ev_rows(cid, t, gid, members):
    rows = []
    for k, (bid, ask, vol, ltp) in enumerate(members):
        rows.append({"capture_id": cid, "cs": t, "neg_risk_market_id": gid, "event_id": f"E{gid}", "market_id": f"{gid}m{k}", "best_bid": bid,
                     "best_ask": ask, "last_trade_price": ltp, "closed": "False", "active": "True", "accepting_orders": 1.0,
                     "neg_risk_other": 0.0, "event_neg_risk_augmented": 0.0, "volume_num": vol, "final_yes": np.nan})
    return rows


def test_never_traded_definition():
    nt = cs.never_traded([np.nan, 0.0, np.nan, 5.0, 0.0], [np.nan, np.nan, 0.4, np.nan, 0.3])
    assert nt.tolist() == [True, True, False, False, False]  # blank volume WITH a last trade is not never-traded


def test_placeholder_setup_gap_and_gate_reads_no_outcome():
    mem = [(0.30, 0.34, 100.0, 0.32), (0.25, 0.29, 100.0, 0.27), (0.10, 0.14, 100.0, 0.12)]  # traded mids .32+.27+.12 = .71 => fair .29
    ph = (0.01, 0.20, np.nan, np.nan)  # quote far below fair; ask .20: fair - ask = .09
    rows = ev_rows("c0", T0, "g1", [*mem, ph])
    df = pd.DataFrame(rows)
    df["final_yes"] = 1.0  # an outcome column that the gate must drop on entry
    out = cs.placeholder_gate(df, {"g1": 4}, days=1)
    assert out["reads_outcomes"] is False and out["unique_setups_gap_ge_5c"] == 1
    assert out["setups_per_day_gap_ge_5c"] == 1.0 and out["gate_pass"] is False  # < 2 per day and < 30 events
    s, why = cs.placeholder_setups(pd.DataFrame(rows), 4)
    assert why == "ok" and s[0]["fair"] == pytest.approx(0.29) and s[0]["gap"] == pytest.approx(0.09)
    # two never-traded members => not a setup; a closed member => excluded (no outcome read to classify it)
    two = ev_rows("c0", T0, "g2", [*mem, ph, (0.02, 0.10, np.nan, np.nan)])
    assert cs.placeholder_setups(pd.DataFrame(two), 5)[1] == "not_exactly_one_never_traded"
    closed = pd.DataFrame(ev_rows("c0", T0, "g3", [*mem, ph]))
    closed.loc[0, "closed"] = "True"
    assert cs.placeholder_setups(closed, 4)[1] == "closed_member"


def test_placeholder_gate_can_pass():
    mem = [(0.30, 0.34, 100.0, 0.32), (0.25, 0.29, 100.0, 0.27), (0.10, 0.14, 100.0, 0.12)]
    rows = []
    for e in range(40):
        for day in range(2):
            rows += ev_rows(f"c{day}", T0 + day * DAY, f"g{e}", [*mem, (0.01, 0.20, np.nan, np.nan)])
    out = cs.placeholder_gate(pd.DataFrame(rows), {f"g{e}": 4 for e in range(40)}, days=2)
    assert out["setups_per_day_gap_ge_5c"] == 40.0 and out["distinct_events_gap_ge_5c"] == 40 and out["gate_pass"] is True


# ---------------------------------------------------------------------------------------------
# network text fetch, windows, logging, runner refusals
# ---------------------------------------------------------------------------------------------


class FakeLimiter:
    def __init__(self):
        self.calls = 0

    def get(self, url, params):
        self.calls += 1
        ids = [v for k, v in params if k == "id"]
        return 200, [{"id": i, "question": f"q{i}", "description": f"d{i}", "createdAt": CREATED, "groupItemTitle": ""} for i in ids if i != "99"]


def test_fetch_question_text_batches_resumes_and_counts_missing(tmp_path):
    lim = FakeLimiter()
    ids = [str(i) for i in range(45)] + ["99"]
    cache = tmp_path / "t.jsonl"
    t1, rep1 = cs.fetch_question_text(ids, lim, cache_path=cache, max_requests=1)
    assert rep1["stopped"] == "max_requests" and not rep1["complete"] and lim.calls == 1
    t2, rep2 = cs.fetch_question_text(ids, lim, cache_path=cache)
    assert rep2["complete"] and lim.calls == 3 and rep2["n_missing"] == 1  # only the remaining batches were requested
    assert t2["3"]["question"] == "q3" and t2["99"]["missing"]


def test_window_guards_and_pin(tmp_path):
    pin = tmp_path / "pin.json"
    doc = cs.pin_rep_start("abcdef1", "2026-10-25T12:00:00+00:00", pin)
    assert doc["t2_rep_start"] == cs.T2_REP_START_FLOOR  # floor binds
    with pytest.raises(cs.RepStartError):
        cs.pin_rep_start("abcdef1", "2026-10-25T12:00:00+00:00", pin)
    doc2 = cs.pin_rep_start("abcdef2", "2026-10-30T12:00:00+00:00", tmp_path / "pin2.json")
    assert doc2["t2_rep_start"] == "2026-10-30T14:00:00Z"
    with pytest.raises(cs.TooEarlyError):
        cs.check_window_allowed("rep", datetime(2026, 11, 20, tzinfo=UTC), pin)
    cs.check_window_allowed("rep", datetime(2026, 11, 24, tzinfo=UTC), pin)
    cs.check_window_allowed("dev")  # dev is never refused here


def test_freeze_list_extends_only(tmp_path):
    doc, ids = build_extract(tmp_path, n_l=1, n_x=0, n_cap=3)
    d = cs.freeze_cb2_list("dev", tmp_path, now=datetime(2026, 10, 25, tzinfo=UTC))
    assert d["n"] == 3 and d["final"] and d["sha256"] == cb.ids_sha256(ids)
    man = json.loads((tmp_path / "manifest.json").read_text())
    del man["captures"]["c2"]
    (tmp_path / "manifest.json").write_text(json.dumps(man))
    with pytest.raises(cs.CaptureListError):
        cs.freeze_cb2_list("dev", tmp_path)


def test_log_trials_kinds_and_count_line(tmp_path):
    path = tmp_path / "trials.jsonl"
    w = cs.log_trials("L", {"L1": {"p": 0.2, "mean": 0.01, "advance": False}, "X2": {"p": 0.9}}, kind=cs.KIND_TEST, role="exploratory_dev",
                      dataset="d", results_path="r", results_sha256="s", run_id="x", prov={}, decl_sha="h",
                      placebo={"X2": {"draws": 10, "n_advance": 0}}, path=path)
    recs = [json.loads(line) for line in path.read_text().splitlines()]
    assert len(w) == 4 and [r["kind"] for r in recs] == ["cb2_test", "cb2_test", "cb2_test", "ml_explain"]
    assert recs[2]["evidence_role"] == "placebo" and recs[3]["n_tests"] == 2 and recs[3]["source"] == "creative_batch_2:L"


def test_kinds_registered_in_battery2_counter():
    from astrolabe.research_lab import battery2

    missing = [k for k in (cs.KIND_TEST, cs.KIND_REP) if k not in battery2.KIND_RULES]
    if missing:
        pytest.skip(f"KIND_RULES entries owned by the weather/KIND_RULES change: {missing}")
    for k in (cs.KIND_TEST, cs.KIND_REP):
        assert battery2.KIND_RULES[k][0] == battery2.EXCLUDE
    battery2.cumulative_count(provenance.REPO_ROOT / "docs" / "research_lab" / "trials.jsonl")


def run_main(argv):
    import run_cb2

    return run_cb2.main(argv)


@pytest.mark.parametrize("rid", ["h5_cb1", "h5_cb1_ladders", "h3_power", "h4_seal"])
def test_runner_refuses_sealed_run_ids(rid, capsys):
    assert run_main(["screen", "--family", "W", "--run-id", rid]) == 3
    assert run_main(["weather-fetch", "--run-id", rid]) == 3
    assert "refused" in capsys.readouterr().out


def test_runner_ladder_list_refuses_without_committed_grouper_hash(tmp_path, monkeypatch, capsys):
    bad = tmp_path / "seal.json"
    bad.write_text(json.dumps({"sha256": "1" * 64}))
    monkeypatch.setattr(cs, "GROUPER_SEAL_FILE", bad)
    assert run_main(["ladder-list", "--extract-root", str(tmp_path / "x"), "--snapshot-root", str(tmp_path / "s")]) == 3
    assert "GrouperRuleError" in capsys.readouterr().out


def test_runner_counted_commands_refuse_without_declaration(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cs, "MODEL_SPEC_FILE", tmp_path / "absent.json")
    assert run_main(["snapshots", "--family", "L", "--window", "dev", "--list-sha256", "x", "--extract-root", str(tmp_path)]) == 3
    assert "DeclarationError" in capsys.readouterr().out
    assert run_main(["screen", "--family", "L", "--list-sha256", "x", "--extract-root", str(tmp_path)]) == 3


def test_runner_rep_snapshots_refused_before_rep_end(tmp_path, monkeypatch, capsys):
    pin = tmp_path / "pin.json"
    cs.pin_rep_start("abcdef1", "2026-12-20T00:00:00+00:00", pin)  # rep window far in the future
    monkeypatch.setattr(cs, "T2_REP_START_FILE", pin)
    assert run_main(["snapshots", "--family", "L", "--window", "rep", "--list-sha256", "x", "--extract-root", str(tmp_path)]) == 3
    assert "TooEarlyError" in capsys.readouterr().out


def test_runner_weather_hooks_exit_2_when_module_missing(monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "astrolabe.research_lab.cb2_weather", None)  # ImportError on import
    import astrolabe.research_lab as rl_pkg

    monkeypatch.delattr(rl_pkg, "cb2_weather", raising=False)  # already imported by other tests in the session
    for argv in (["weather-fetch"], ["seal"], ["verify-seal"], ["stagep", "--family", "W"], ["screen", "--family", "W"],
                 ["replicate", "--family", "W"]):
        assert run_main(argv) == 2, argv
    assert "cb2_weather is not available" in capsys.readouterr().err


def test_runner_p_family_has_no_screen(capsys):
    assert run_main(["screen", "--family", "P"]) == 0
    assert "counts-only" in capsys.readouterr().out


def test_universe_excludes_negrisk_sports_weather_and_closed_and_picks_daily_captures(tmp_path):
    def cap(name, started):
        d = tmp_path / name
        d.mkdir()
        (d / "manifest.json").write_text(json.dumps({"state": "complete", "started_utc": started, "capture_id": name}))
        rows = pd.DataFrame({"market_id": ["1", "2", "3", "4", "5"], "event_id": ["e1", "e2", "e3", "e4", "e5"],
                             "neg_risk_market_id": ["", "nr", "", "", ""], "closed": ["False", "False", "False", "False", "True"],
                             "best_bid": 0.4, "best_ask": 0.5})
        rows.to_csv(d / "rows.csv.gz", index=False)
        pd.DataFrame({"market_id": ["1", "2", "3", "4", "5"], "fee_category": ["politics", "politics", "sports", "weather", "politics"]}
                     ).to_csv(d / "rows_ext.csv.gz", index=False)

    cap("a", "2026-10-11T12:31:00Z")
    cap("b", "2026-10-11T18:31:00Z")  # same day, later: not the daily capture, not the latest
    cap("c", "2026-10-12T12:31:00Z")
    cap("d", "2026-10-12T14:31:00Z")  # the latest capture is added
    caps = cs.universe_captures(tmp_path, cs.T2_DEV_START)
    assert [c["capture_id"] for c in caps] == ["a", "c", "d"]
    uni, rep = cs.read_universe(caps)
    assert sorted(uni["market_id"]) == ["1"] and rep["captures"] == 3
