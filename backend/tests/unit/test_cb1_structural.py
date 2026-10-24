# ruff: noqa: E501
"""CB1 structural tests D (neg-risk set) and B (near-rung NO carry). Synthetic fixtures only; no network, no real data."""

from __future__ import annotations

import gzip
import json
import math
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import battery2, forecast, h5_seal, provenance
from astrolabe.research_lab import cb1_structural as cs

DAY = 86400.0
H = 3600.0
T0 = cs._ep("2026-10-12T00:00:00Z")


def iso(t: float) -> str:
    return datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------------------------
# D fixtures
# ---------------------------------------------------------------------------------------------


def _member(cid, t, gid, k, ask, bid=None, **kw):
    r = {"capture_id": cid, "capture_start_utc": iso(t), "received_utc": iso(t + 300), "neg_risk_market_id": gid,
         "event_id": f"E{gid}", "market_id": f"{gid}m{k}", "clob_token_id_0": f"tok{gid}{k}",
         "best_bid": ask - 0.02 if bid is None else bid, "best_ask": ask, "spread": 0.02,
         "last_trade_price": ask - 0.01, "closed": "False", "active": "True", "accepting_orders": 1.0,
         "neg_risk_other": 0.0, "event_neg_risk_augmented": 0.0, "volume_num": 100.0, "fee_schedule": "",
         "fee_category": "politics", "end_date": iso(T0 + 30 * DAY), "fees_enabled": 1.0,
         "sw1_best_ask": np.nan, "sw1_ask_size_1": np.nan, "sw2_best_ask": np.nan, "sw2_ask_size_1": np.nan}
    r.update(kw)
    return r


def _event_rows(cid, t, gid, asks, **kw):
    return [_member(cid, t, gid, k, a, **kw) for k, a in enumerate(asks)]


def make_extract(root: Path, captures: list[tuple[str, float, list[dict]]], members: dict[str, int],
                 *, final: bool = True, missing: list[str] | None = None, until: str = cs.T_DEV_END,
                 from_utc: str = cs.T_DEV_START, name: str = "dev") -> dict:
    (root / "negrisk").mkdir(parents=True, exist_ok=True)
    (root / "capture_lists").mkdir(exist_ok=True)
    man = {"captures": {}}
    ids = []
    for cid, t, rows in captures:
        ids.append(cid)
        man["captures"][cid] = {"started_utc": iso(t), "status": "extracted"}
        pd.DataFrame(rows).to_csv(root / "negrisk" / f"{cid}.csv.gz", index=False)
    (root / "manifest.json").write_text(json.dumps(man))
    pd.DataFrame({"neg_risk_market_id": list(members), "member_count": list(members.values()),
                  "fetched_utc": "2026-01-01T00:00:00Z"}).to_csv(
        root / "event_members.csv.gz", index=False)
    ids = sorted(ids)
    doc = {"kind": name, "from_utc": from_utc, "until": until, "final": final, "capture_ids": ids, "n": len(ids),
           "sha256": cs.capture_list_sha256(ids), "missing_ids": missing or []}
    (root / "capture_lists" / f"{name}.json").write_text(json.dumps(doc))
    return doc


def many_events(n_ev=60, n_cap=6, asks_fn=None, seed=0):
    """n_ev 3-member events over n_cap captures 2h apart starting T0. asks_fn(ev, cap, rng)->list of asks."""
    rng = np.random.default_rng(seed)
    asks_fn = asks_fn or persistent_cheap
    caps, members = [], {}
    for j in range(n_cap):
        t = T0 + 2 * H * j
        rows = []
        for e in range(n_ev):
            gid = f"G{e}"
            members[gid] = 3
            rows += _event_rows(f"c{j:02d}", t, gid, asks_fn(e, j, rng))
        caps.append((f"c{j:02d}", t, rows))
    return caps, members


def persistent_cheap(e, j, rng):  # sum asks = 0.90 -> C ~ 0.90+fees; persists at the next capture
    return [0.30, 0.30, 0.30]


# ---------------------------------------------------------------------------------------------
# eligibility
# ---------------------------------------------------------------------------------------------


def _grp(**over):
    rows = _event_rows("c0", T0, "G1", [0.3, 0.3, 0.3])
    df = pd.DataFrame(rows)
    for k, v in over.items():
        df.loc[0, k] = v
    return df


@pytest.mark.parametrize("over,why", [
    ({"event_neg_risk_augmented": 1.0}, "augmented"),
    ({"event_neg_risk_augmented": np.nan}, "augmented_unknown"),
    ({"neg_risk_other": 1.0}, "other"),
    ({"neg_risk_other": np.nan}, "other_unknown"),
    ({"active": "False"}, "member_not_open"),
    ({"accepting_orders": 0.0}, "member_not_open"),
    ({"accepting_orders": np.nan}, "member_not_open"),
    ({"closed": "True"}, "closed_without_final_outcome"),
    ({"closed": "True", "final_yes": 1.0}, "member_resolved_yes"),
    ({"best_bid": 0.0}, "bad_quote"),
    ({"volume_num": 0.0}, "no_volume"),
])
def test_ineligible_reasons(over, why):
    g = _grp(**over)
    if "final_yes" in over:
        g["final_yes"] = [1.0, np.nan, np.nan]
    res, reason = cs._group_eligible(g, 3)
    assert res is None and reason == why


def test_member_count_mismatch_and_missing_count():
    g = _grp()
    assert cs._group_eligible(g, 4)[1] == "member_count_mismatch"
    assert cs._group_eligible(g, None)[1] == "no_member_count"
    assert cs._group_eligible(g, 3)[1] == "ok"


def test_closed_no_member_excluded_from_sums_only_with_final_outcome():
    rows = _event_rows("c0", T0, "G1", [0.3, 0.3, 0.3, 0.05])
    g = pd.DataFrame(rows)
    g.loc[3, "closed"] = "True"
    res, why = cs._group_eligible(g, 4)
    assert res is None and why == "closed_without_final_outcome"
    res, why = cs._group_eligible(g, 4, {"G1m3": 0.0})
    assert why == "ok" and len(res["legs"]) == 3 and res["S_ask"] == pytest.approx(-0.1)
    # an OPEN member's outcome is never consulted
    res, why = cs._group_eligible(pd.DataFrame(_event_rows("c0", T0, "G1", [0.3, 0.3, 0.3])), 3,
                                  {"G1m0": 1.0, "G1m1": 1.0})
    assert why == "ok"


def test_set_cost_sums_fees_per_leg():
    asks = [0.3, 0.3, 0.3]
    c = cs.set_cost(asks, [0.04, 0.04, 0.0], [1.0, 1.0, 1.0])
    assert c == pytest.approx(0.9 + 2 * 0.04 * 0.21)
    r, e = cs.leg_rate(None, "politics")
    assert r == 0.04 and e == 1.0 and cs.leg_rate(None, None)[0] == 0.07 and cs.leg_rate(None, "geopolitics")[0] == 0.0


def test_next_capture_pairs_drops_outage_gap():
    cs_by = {"a": 0.0, "b": 2 * H, "c": 12 * H, "d": 14 * H}
    nxt, cnt = cs.next_capture_pairs(cs_by)
    assert nxt == {"a": "b", "c": "d"} and cnt["excluded_gap"] == 1 and cnt["kept"] == 2


# ---------------------------------------------------------------------------------------------
# window / capture-list guards
# ---------------------------------------------------------------------------------------------


def test_window_guard_rejects_capture_at_t_dev_end(tmp_path):
    t_end = cs._ep(cs.T_DEV_END)
    caps, members = many_events(2, 1)
    caps = [("c00", t_end, caps[0][2])]
    make_extract(tmp_path, caps, members)
    cl = cs.load_capture_list(tmp_path / "capture_lists" / "dev.json", window="dev")
    with pytest.raises(cs.WindowError):
        cs.load_window_captures(tmp_path, cl, "dev")


def _pin(monkeypatch, tmp_path, start="2026-10-19T00:00:00Z"):
    f = tmp_path / "cb1_t_rep_start.json"
    f.write_text(json.dumps({"t_rep_start": start}))
    monkeypatch.setattr(cs, "T_REP_START_FILE", f)
    return f


def test_rep_refused_before_t_rep_end_and_floor(tmp_path, monkeypatch):
    with pytest.raises(cs.TooEarlyError):
        cs.check_window_allowed("rep", datetime(2026, 11, 8, tzinfo=UTC))
    cs.check_window_allowed("rep", datetime(2026, 11, 9, tzinfo=UTC))
    _pin(monkeypatch, tmp_path)
    with pytest.raises(cs.WindowError):  # a free value (here before the floor) never overrides the pin
        cs.window_bounds("rep", "2026-10-18T00:00:00Z")
    cs.check_window_allowed("dev", datetime(2026, 10, 1, tzinfo=UTC))


def test_pin_rep_start_derivation_and_never_overwritten(tmp_path):
    f = tmp_path / "pin.json"
    doc = cs.pin_rep_start("abcdef1", "2026-10-20T10:00:00+01:00", f)  # 09:00Z + 2h
    assert doc["t_rep_start"] == "2026-10-20T11:00:00Z" and cs.load_pinned_rep_start(f) == "2026-10-20T11:00:00Z"
    with pytest.raises(cs.RepStartError):
        cs.pin_rep_start("abcdef1", "2026-10-21T10:00:00Z", f)
    g = tmp_path / "early.json"  # before the floor + 2h: the declared floor applies
    assert cs.pin_rep_start("abcdef1", "2026-10-16T00:00:00Z", g)["t_rep_start"] == cs.T_REP_START_FLOOR
    with pytest.raises(cs.RepStartError):
        cs.pin_rep_start("not-a-sha!", "2026-10-16T00:00:00Z", tmp_path / "x.json")
    with pytest.raises(cs.RepStartError):
        cs.load_pinned_rep_start(tmp_path / "absent.json")


def test_rep_capture_list_from_utc_must_equal_pin(tmp_path, monkeypatch):
    _pin(monkeypatch, tmp_path, "2026-10-20T11:00:00Z")
    caps, members = many_events(2, 2)
    p = tmp_path / "capture_lists" / "rep.json"
    make_extract(tmp_path, caps, members, name="rep", until=cs.T_REP_END, from_utc="2026-10-20T11:00:00Z")
    assert cs.load_capture_list(p, window="rep")["ids"]
    make_extract(tmp_path, caps, members, name="rep", until=cs.T_REP_END, from_utc="2026-10-19T00:00:00Z")
    with pytest.raises(cs.CaptureListError, match="pinned"):
        cs.load_capture_list(p, window="rep")
    make_extract(tmp_path, caps, members, name="rep", until=cs.T_REP_END, from_utc="")
    with pytest.raises(cs.CaptureListError, match="pinned"):
        cs.load_capture_list(p, window="rep")


def test_capture_list_guards(tmp_path):
    caps, members = many_events(2, 2)
    doc = make_extract(tmp_path, caps, members)
    p = tmp_path / "capture_lists" / "dev.json"
    assert cs.load_capture_list(p, doc["sha256"], window="dev")["ids"] == ["c00", "c01"]
    with pytest.raises(cs.CaptureListError):
        cs.load_capture_list(p, "0" * 64, window="dev")
    make_extract(tmp_path, caps, members, final=False)  # not final
    with pytest.raises(cs.CaptureListError):
        cs.load_capture_list(p, window="dev")
    bad = dict(doc, sha256="f" * 64, final=True)
    p.write_text(json.dumps(bad))
    with pytest.raises(cs.CaptureListError):
        cs.load_capture_list(p, window="dev")
    p.write_text(json.dumps({**doc, "until": "2026-10-16T00:00:00Z"}))
    with pytest.raises(cs.CaptureListError):
        cs.load_capture_list(p, window="dev")


def test_missing_ids_counted_and_listed_but_absent_table_raises(tmp_path):
    caps, members = many_events(2, 3)
    doc = make_extract(tmp_path, caps, members)
    # c02 never extracted: declared missing -> counted, skipped
    ids = doc["capture_ids"]
    (tmp_path / "negrisk" / "c02.csv.gz").unlink()
    man = json.loads((tmp_path / "manifest.json").read_text())
    man["captures"].pop("c02")
    (tmp_path / "manifest.json").write_text(json.dumps(man))
    p = tmp_path / "capture_lists" / "dev.json"
    p.write_text(json.dumps({**doc, "missing_ids": ["c02"]}))
    cl = cs.load_capture_list(p, window="dev")
    df, cs_by, cnt = cs.load_window_captures(tmp_path, cl, "dev")
    assert cnt["missing_listed"] == 1 and set(cs_by) == {"c00", "c01"} and ids == ["c00", "c01", "c02"]
    # listed, not declared missing, table gone -> loud
    (tmp_path / "negrisk" / "c01.csv.gz").unlink()
    with pytest.raises(forecast.ArchivedDataError):
        cs.load_window_captures(tmp_path, cl, "dev")


# ---------------------------------------------------------------------------------------------
# triggers: causality and no-trade rules
# ---------------------------------------------------------------------------------------------


def _ec(caps, members, outcomes=None):
    df = pd.concat([pd.DataFrame(r).assign(cs=t) for _, t, r in caps], ignore_index=True)
    df["capture_id"] = df["capture_id"].astype(str)
    return cs.negrisk_event_captures(df, members, outcomes)[0], {c: t for c, t, _ in caps}


def test_trigger_executes_at_next_capture_price_only():
    def fn(e, j, rng):
        return {0: [0.30, 0.30, 0.30], 1: [0.31, 0.31, 0.31], 2: [0.10, 0.10, 0.10]}.get(j, [0.5, 0.5, 0.5])
    caps, members = many_events(1, 3, fn)
    ec, starts = _ec(caps, members)
    nxt, _ = cs.next_capture_pairs(starts)
    trig, cnt = cs.d2_triggers(ec, nxt)
    assert cnt["triggers"] == 2 and cnt["no_next_or_gap"] == 1  # c00, c01 execute; c02 triggers but has no next
    row = trig[trig["capture_id"] == "c00"].iloc[0]
    c1 = float(ec[ec["capture_id"] == "c01"]["C"].iloc[0])
    assert row["executed"] and row["net"] == pytest.approx(1.0 - c1)  # c01 price, never c00, never c02
    assert row["K"] == pytest.approx(c1)


def test_membership_change_or_missing_ask_means_no_trade_kept_in_denominator():
    def fn(e, j, rng):
        return [0.30, 0.30, 0.30]
    caps, members = many_events(1, 2, fn)
    # c01: one member's ask is missing -> ineligible at c' -> no trade
    caps[1][2][1]["best_ask"] = np.nan
    ec, starts = _ec(caps, members)
    nxt, _ = cs.next_capture_pairs(starts)
    trig, cnt = cs.d2_triggers(ec, nxt)
    assert len(trig) == 1 and not trig.iloc[0]["executed"] and trig.iloc[0]["net"] == 0.0
    assert cnt["no_trade"] == 1 and cnt["executed"] == 0


def test_gap_filter_excludes_pair_without_repair():
    caps, members = many_events(1, 2, persistent_cheap)
    caps[1] = (caps[1][0], caps[1][1] + 10 * H, [dict(r, capture_start_utc=iso(caps[1][1] + 10 * H)) for r in caps[1][2]])
    ec, starts = _ec(caps, members)
    nxt, pc = cs.next_capture_pairs(starts)
    trig, cnt = cs.d2_triggers(ec, nxt)
    assert len(trig) == 0 and cnt["no_next_or_gap"] >= 1 and pc["excluded_gap"] == 1


def test_realised_payout_and_single_winner():
    assert cs.realised_set_payout({"a": 1.0, "b": 0.0}, ["a", "b"]) == (1.0, True, True)
    assert cs.realised_set_payout({"a": 0.5, "b": 0.5}, ["a", "b"])[2] is False
    assert cs.realised_set_payout({"a": 0.0, "b": 0.0}, ["a", "b"]) == (0.0, True, False)
    assert cs.realised_set_payout({"a": 1.0}, ["a", "b"])[1] is False


# ---------------------------------------------------------------------------------------------
# D end to end: determinism, caps, counting
# ---------------------------------------------------------------------------------------------


def _run_d(tmp_path, caps, members, outcomes=None, **kw):
    make_extract(tmp_path, caps, members)
    cl = cs.load_capture_list(tmp_path / "capture_lists" / "dev.json", window="dev")
    return cs.run_negrisk(tmp_path, cl, "dev", n_boot=100, dev=True, alpha=0.01, placebo_draws=20,
                          outcomes=outcomes, **kw)


def test_run_negrisk_deterministic_and_inconclusive_caps(tmp_path):
    caps, members = many_events(60, 6, persistent_cheap)
    r1 = _run_d(tmp_path / "a", caps, members)
    r2 = _run_d(tmp_path / "b", caps, members)
    assert json.dumps(cs._clean(r1), sort_keys=True) == json.dumps(cs._clean(r2), sort_keys=True)
    d2 = r1["tests"]["D2"]
    assert d2["testable"] and d2["mean"] > 0.005  # cheap persistent set: paper net well above the floor
    # no outcomes -> payoff unverified; no sweep data -> depth unverified: never an advance
    assert d2["cap"] and d2["advance"] is False and d2["stage_gate_passed"] in (True, False)
    assert r1["tests"]["D1"]["incidence"]["U"] == 1.0 and r1["tests"]["D1"]["incidence"]["O"] == 0.0


def test_d2_advances_with_realised_payout_and_depth(tmp_path):
    caps, members = many_events(60, 6, persistent_cheap)
    for _, _, rows in caps:
        for r in rows:
            r["sw1_best_ask"], r["sw1_ask_size_1"] = r["best_ask"], 50.0
    outcomes = {f"G{e}m{k}": (1.0 if k == 0 else 0.0) for e in range(60) for k in range(3)}
    res = _run_d(tmp_path, caps, members, outcomes)
    d2 = res["tests"]["D2"]
    assert d2["realised"]["same_sign"] and d2["realised"]["ceiling_ok"] and d2["depth"]["same_sign"]
    assert d2["cap"] is None
    # an anomalous (non single-winner) share above 2% blocks the advance
    bad = dict(outcomes)
    for e in range(10):
        bad[f"G{e}m1"] = 1.0
    res2 = _run_d(tmp_path / "x", caps, members, bad)
    assert res2["tests"]["D2"]["realised"]["ceiling_ok"] is False and res2["tests"]["D2"]["advance"] is False


def test_placebo_calibrated_without_persistence(tmp_path):
    def fn(e, j, rng):  # prices independent across captures: trigger rarely, no persistence
        base = 0.30 if rng.random() < 0.5 else 0.36
        return [base, base, base]
    caps, members = many_events(60, 6, fn, seed=3)
    res = _run_d(tmp_path, caps, members)
    assert res["placebo"]["D2"]["advance_rate"] <= cs.PLACEBO_MAX_ADVANCE_RATE and res["placebo"]["D2"]["calibrated"]


def test_too_few_trigger_events_is_not_testable(tmp_path):
    caps, members = many_events(5, 4, persistent_cheap)
    res = _run_d(tmp_path, caps, members)
    assert res["tests"]["D2"]["testable"] is False and res["tests"]["D2"]["advance"] is False and res["tests"]["D2"]["p"] == 1.0


def test_census_has_counts_only(tmp_path):
    caps, members = many_events(10, 3, persistent_cheap)
    make_extract(tmp_path, caps, members)
    cl = cs.load_capture_list(tmp_path / "capture_lists" / "dev.json", window="dev")
    c = cs.census_negrisk(cs.build_negrisk(tmp_path, cl, "dev"))
    assert c["n_event_clusters"] == 10 and c["n_trigger_events"] == 10
    text = json.dumps(c)
    assert not any(f'"{k}"' in text for k in ("mean", "p", "incidence", "net", "U", "O"))  # counts only


def test_leave_one_day_out_binding_in_dev():
    n = 200
    ev = np.array([f"e{i % 50}" for i in range(n)])
    day = np.array(["d1"] * 100 + ["d2"] * 100)
    net = np.full(n, 0.02)
    net[:100] = 0.02
    ok = cs.mean_gate(net, ev, day, floor=0.005, alpha=0.01, n_boot=50, lodo=True)
    assert ok["leave_one_day_out"] and set(ok["leave_one_day_out"]) == {"d1", "d2"}
    net2 = np.where(day == "d1", 0.08, -0.001)  # positive mean but d1-out is negative
    bad = cs.mean_gate(net2, ev, day, floor=0.005, alpha=0.5, n_boot=50, lodo=True)
    assert bad["advance"] is False


# ---------------------------------------------------------------------------------------------
# trial logging and counting
# ---------------------------------------------------------------------------------------------


def test_log_trials_counts(tmp_path):
    tp = tmp_path / "trials.jsonl"
    tests = {"D1": {"p": 0.2, "mean": 0.01, "advance": False}, "D2": {"p": 0.3, "mean": 0.0, "advance": False}}
    placebo = {"D2": {"draws": 20, "n_advance": 0, "advance_rate": 0.0, "calibrated": True}}
    cs.log_trials("D", tests, kind=cs.KIND_TEST, role="exploratory_dev", dataset="x", results_path="r", results_sha256="s",
                  run_id="r1", prov={}, decl_sha="d", placebo=placebo, path=tp)
    recs = [json.loads(x) for x in tp.read_text().splitlines()]
    assert [r["kind"] for r in recs] == [cs.KIND_TEST, cs.KIND_TEST, cs.KIND_TEST, "ml_explain"]
    assert recs[2]["evidence_role"] == "placebo" and recs[3]["n_tests"] == 2 and recs[3]["source"] == "creative_batch_1:D"
    assert battery2.cumulative_count(tp)["total"] == 2  # per-test lines excluded; placebo 0; count line n_tests
    cs.log_trials("D", {"D1": tests["D1"]}, kind=cs.KIND_REP, role="exploratory_dev", dataset="x", results_path="r",
                  results_sha256="s", run_id="r2", prov={}, decl_sha="d", path=tp)
    cs.log_trials("B3", {"B3": tests["D1"]}, kind=cs.KIND_PROSP, role="prospective_confirmation", dataset="x",
                  results_path="r", results_sha256="s", run_id="r3", prov={}, decl_sha="d", path=tp)
    assert battery2.cumulative_count(tp)["total"] == 4


def test_kind_rules_present_and_real_trials_still_count():
    for k in (cs.KIND_TEST, cs.KIND_REP, cs.KIND_PROSP):
        assert battery2.KIND_RULES[k][0] == battery2.EXCLUDE
    assert battery2.cumulative_count(provenance.TRIALS_PATH)["total"] > 0


# ---------------------------------------------------------------------------------------------
# declaration guard
# ---------------------------------------------------------------------------------------------


def test_declaration_guard(tmp_path):
    p = tmp_path / "decl.json"
    with pytest.raises(cs.DeclarationError):
        cs.require_declaration(p)
    rec = cs.write_declaration(p)
    assert cs.require_declaration(p) == rec["declaration_sha256"] == cs.declaration_sha256()
    with pytest.raises(cs.DeclarationError):
        cs.write_declaration(p)  # never rewritten
    doc = json.loads(p.read_text())
    doc["declaration_sha256"] = "0" * 64
    p.write_text(json.dumps(doc))
    with pytest.raises(cs.DeclarationError):
        cs.require_declaration(p)


# ---------------------------------------------------------------------------------------------
# B: near-rung origins
# ---------------------------------------------------------------------------------------------

B0 = cs._ep("2025-01-01T00:00:00Z")


def rung(mid, dl_days, closed_time="", closed=False, outcome="", created=-5):
    return {"market_id": str(mid), "question": f"q{mid}", "deadline": B0 + dl_days * DAY,
            "token_yes": f"t{mid}", "created_at": iso(B0 + created * DAY), "closed_time": closed_time,
            "closed": closed, "outcome_prices": outcome, "outcomes": ""}


def ladder(lid, rungs):
    return {"ladder_id": f"{lid}:x", "event_id": str(lid), "stem": "s", "title": "", "rungs": rungs}


def flat(v, start=-5, end=30):
    ts = np.arange(B0 + start * DAY, B0 + end * DAY, H)
    return ts, np.full(len(ts), v)


def make_fns(series_by, trades_by=None, trunc=None):
    trades_by = trades_by or {}
    trunc = trunc or {}
    return (lambda m: series_by.get(m)), (lambda m: (trades_by.get(m, np.array([B0 - 4 * DAY])), trunc.get(m, False)))


GRID = np.arange(B0, B0 + 20 * DAY, 6 * H)


def test_near_origin_uses_only_past_data_and_one_origin_per_rung():
    L = ladder(1, [rung(10, 10), rung(11, 20)])
    sa = {"10": flat(0.30), "11": flat(0.40)}
    u, ex = cs.near_rung_origins(L, *make_fns(sa), GRID)
    assert len(u) == 1 and u[0]["near_id"] == "10" and u[0]["t"] == GRID[0] and not ex
    # planted spike AFTER the first origin must not move the selected origin or its price
    ts, v = flat(0.30)
    v = v.copy()
    v[ts > GRID[0] + 2 * H] = 0.55
    sb = {"10": (ts, v), "11": flat(0.60)}
    u2, _ = cs.near_rung_origins(L, *make_fns(sb), GRID)
    assert u2[0]["t"] == GRID[0] and u2[0]["v1"] == pytest.approx(0.30)
    # the price at t uses a point stamped <= t - 1h (lag)
    ts3 = np.array([GRID[0] - 5 * H, GRID[0] - 0.5 * H])
    u3, _ = cs.near_rung_origins(L, *make_fns({"10": (ts3, np.array([0.20, 0.50])), "11": flat(0.6)}), GRID)
    assert u3[0]["v1"] == pytest.approx(0.20)


def test_planted_early_close_of_later_rung_does_not_change_near_before_close():
    base = [rung(10, 10), rung(11, 20), rung(12, 25)]
    sa = {"10": flat(0.30), "11": flat(0.40), "12": flat(0.45)}
    u1, _ = cs.near_rung_origins(ladder(1, base), *make_fns(sa), GRID)
    later = [rung(10, 10), rung(11, 20, closed_time=iso(B0 + 8 * DAY), closed=True, outcome='["1","0"]'), rung(12, 25)]
    u2, _ = cs.near_rung_origins(ladder(1, later), *make_fns(sa), GRID)
    assert u1[0]["t"] == u2[0]["t"] == GRID[0] and u1[0]["near_id"] == u2[0]["near_id"]
    assert u1[0]["far_id"] == "11" and u2[0]["far_id"] == "11"  # open at t (closed_time is later than t)


def test_two_day_rule_range_and_monotone_filters():
    L = ladder(1, [rung(10, 1.5), rung(11, 20)])  # near rung has < 2 days left at every origin
    u, _ = cs.near_rung_origins(L, *make_fns({"10": flat(0.3), "11": flat(0.4)}), GRID)
    assert u == []  # rung 10 is never near (< 2 days left); rung 11 has no far rung
    L2 = ladder(2, [rung(10, 10), rung(11, 20)])
    assert cs.near_rung_origins(L2, *make_fns({"10": flat(0.70), "11": flat(0.8)}), GRID)[0] == []  # v1 > 0.60
    assert cs.near_rung_origins(L2, *make_fns({"10": flat(0.40), "11": flat(0.3)}), GRID)[0] == []  # not consistent
    assert len(cs.near_rung_origins(L2, *make_fns({"10": flat(0.40), "11": flat(0.395)}), GRID)[0]) == 1  # within tol


def test_truncated_market_unavailable_excludes_never_zero():
    L = ladder(1, [rung(10, 10), rung(11, 20)])
    sa = {"10": flat(0.30), "11": flat(0.40)}
    # truncated and the stored trades all start AFTER t -> unavailable -> excluded and counted
    late = np.array([GRID[0] + 30 * DAY])
    u, ex = cs.near_rung_origins(L, *make_fns(sa, {"10": late}, {"10": True}), GRID)
    assert u == [] and len(ex) == 1 and ex[0]["reason"] == "trade_condition_unavailable"
    # same trades in a COMPLETE market: condition is False (not unavailable) -> keep scanning, trade appears later
    u2, ex2 = cs.near_rung_origins(L, *make_fns(sa, {"10": np.array([GRID[3] - H])}, {"10": False}), GRID)
    assert not ex2 and len(u2) == 1 and u2[0]["t"] == GRID[3]
    # truncated but a stored trade already satisfies it -> known true
    u3, _ = cs.near_rung_origins(L, *make_fns(sa, {"10": np.array([B0 - 4 * DAY])}, {"10": True}), GRID)
    assert len(u3) == 1
    assert cs.trade_before(None, False, 1.0) is None
    assert cs.trade_before(np.array([]), False, 1.0) is False and cs.trade_before(np.array([]), True, 1.0) is None


def test_far_rung_validity_and_no_ask_floor():
    L = ladder(1, [rung(10, 10), rung(11, 20)])
    u, _ = cs.near_rung_origins(L, *make_fns({"10": flat(0.30), "11": flat(0.99)}), GRID)
    assert u[0]["far_valid"] is False
    a, f = cs.no_ask(0.30)
    assert a == pytest.approx(0.70 + 0.011) and f > 0  # NO price 0.70: band 0.20-0.80, h = 1.1c
    assert cs.no_ask(0.99)[0] == pytest.approx(0.01 + 0.0205)
    assert cs.no_ask(0.0)[0] <= 0.999
    # section 2.1 band table
    for p, h in ((0.03, 0.0205), (0.10, 0.015), (0.50, 0.011), (0.85, 0.015), (0.97, 0.0125), (0.999, 0.0125)):
        assert cs.half_spread(p) == h


def test_ladder_pnl_resolved_censored_and_week_cluster():
    yes_no = rung(10, 10, closed_time=iso(B0 + 11 * DAY), closed=True, outcome='["0","1"]')  # YES lost: NO wins
    L = ladder(1, [yes_no, rung(11, 20)])
    sa = {"10": flat(0.30), "11": flat(0.40)}
    u, _ = cs.near_rung_origins(L, *make_fns(sa), GRID)
    df = cs.ladder_pnl(u, lambda m: sa.get(m), B0 + 400 * DAY)
    r = df.iloc[0]
    assert r["status"] == "resolved" and r["net"] == pytest.approx(1.0 - r["a"] - r["f"])
    assert r["week"] == pd.Timestamp(B0 + 10 * DAY, unit="s", tz="UTC").strftime("%G-W%V")  # deadline week
    assert r["far_status"] == "censored_no_price"  # far rung unresolved, last price older than 12h at the censor date
    # unresolved at censor: marked at the last as-of NO price minus h and exit fee, flagged
    L2 = ladder(2, [rung(20, 10), rung(21, 20)])
    sb = {"20": flat(0.30, end=15), "21": flat(0.40, end=15)}
    u2, _ = cs.near_rung_origins(L2, *make_fns(sb), GRID)
    d2 = cs.ladder_pnl(u2, lambda m: sb.get(m), B0 + 14 * DAY)
    assert d2.iloc[0]["censored"] and d2.iloc[0]["status"] == "censored"
    z = cs.ladder_pnl(u2, lambda m: sb.get(m), B0 + 14 * DAY, cens_value=0.0).iloc[0]["net"]
    assert z == pytest.approx(-(u2[0]["a"] + u2[0]["f"]))
    # closed without a parseable outcome is excluded (NaN) and labelled
    L3 = ladder(3, [rung(30, 10, closed_time=iso(B0 + 11 * DAY), closed=True, outcome=""), rung(31, 20)])
    u3, _ = cs.near_rung_origins(L3, *make_fns({"30": flat(0.3), "31": flat(0.4)}), GRID)
    d3 = cs.ladder_pnl(u3, lambda m: flat(0.3), B0 + 400 * DAY)
    assert d3.iloc[0]["status"] == "closed_no_outcome" and math.isnan(d3.iloc[0]["net"])


def test_censor_margin_restricts_origins():
    L = ladder(1, [rung(10, 10), rung(11, 20)])
    sa = {"10": flat(0.30), "11": flat(0.40)}
    u, _ = cs.near_rung_origins(L, *make_fns(sa), GRID, t_censor=GRID[0] + 59 * DAY)  # origin > censor - 60d
    assert u == []


def test_exclusion_guards():
    L1, L2, L3 = (ladder(1, [rung(10, 10), rung(11, 20)]), ladder(2, [rung(20, 10), rung(21, 20)]),
                  ladder(3, [rung(30, 10), rung(31, 20)]))
    kept, rep = cs.apply_exclusions([L1, L2, L3], {"events": {"1"}, "markets": {"21"}})
    assert [x["event_id"] for x in kept] == ["3"] and rep["dropped_event_id"] == 1 and rep["dropped_rung_id"] == 1


# ---------------------------------------------------------------------------------------------
# B R1 end to end on a sealed synthetic run (access log, seal refusal, determinism)
# ---------------------------------------------------------------------------------------------


def make_run(root: Path, n_lad=130, seed=1) -> Path:
    rng = np.random.default_rng(seed)
    run = root / "h5_cb1_ladders"
    (run / "prices").mkdir(parents=True)
    (run / "trades").mkdir()
    lad, prog = [], []
    for i in range(n_lad):
        yes_a = float(rng.random() < 0.3)
        ra = rung(1000 + 2 * i, 10, closed_time=iso(B0 + 11 * DAY), closed=True, outcome=json.dumps([str(yes_a), str(1 - yes_a)]))
        rb = rung(1001 + 2 * i, 20, closed_time=iso(B0 + 21 * DAY), closed=True, outcome='["0","1"]')
        lad.append(ladder(i, [ra, rb]))
        for r, v in ((ra, 0.30), (rb, 0.40)):
            ts, vals = flat(v, end=12)
            pd.DataFrame({"t": ts, "p": vals}).to_csv(run / "prices" / f"{r['market_id']}.csv.gz", index=False)
            pd.DataFrame({"ts": [B0 - 4 * DAY]}).to_csv(run / "trades" / f"{r['market_id']}.csv.gz", index=False)
            prog.append({"market_id": r["market_id"], "status": "done", "trades_truncated": False})
    with gzip.open(run / "ladders.jsonl.gz", "wt") as fh:
        for x in lad:
            fh.write(json.dumps(x) + "\n")
    (run / "progress.jsonl").write_text("\n".join(json.dumps(p) for p in prog) + "\n")
    (run / "manifest.json").write_text(json.dumps({"run_id": "h5_cb1_ladders", "stopped": None, "complete": True,
                                                   "request_clock_now": iso(B0 + 700 * DAY)}))
    return run


def test_ladders_r1_requires_seal_and_committed_copy_and_logs_access(tmp_path):
    run = make_run(tmp_path)
    seals = tmp_path / "seals"
    seals.mkdir()
    with pytest.raises(cs.SealUnavailableError):  # not sealed
        cs.run_ladders_r1(run, n_boot=50, decl_sha="d", job="t", min_ladders=1, seals_dir=seals)
    seal = h5_seal.seal_run(run, trials_path=tmp_path / "t.jsonl", allow_incomplete=True)
    with pytest.raises(cs.SealUnavailableError):  # no committed copy
        cs.run_ladders_r1(run, n_boot=50, decl_sha="d", job="t", min_ladders=1, seals_dir=seals)
    (seals / "h5_cb1_ladders_SEAL.json").write_text(json.dumps({"listing_sha256": "0" * 64}))
    with pytest.raises(cs.SealUnavailableError):  # mismatching copy
        cs.run_ladders_r1(run, n_boot=50, decl_sha="d", job="t", min_ladders=1, seals_dir=seals)
    (seals / "h5_cb1_ladders_SEAL.json").write_text(json.dumps({"listing_sha256": seal["listing_sha256"]}))
    res = cs.run_ladders_r1(run, n_boot=50, decl_sha="d", job="t", min_ladders=1, seals_dir=seals, placebo_draws=20)
    log = (run / "ACCESS_LOG.jsonl").read_text().splitlines()
    assert len(log) == 1 and json.loads(log[0])["job"] == "t"
    assert res["n_units"] == 130 and res["status_counts"] == {"resolved": 130}
    b1 = res["tests"]["B1"]
    assert b1["testable"] and "mean" in b1 and res["holm_pending"] and set(res["tests"]) == {"B1", "B2"}
    assert res["placebo"]["B1"]["calibrated"]
    res2 = cs.run_ladders_r1(run, n_boot=50, decl_sha="d", job="t", min_ladders=1, seals_dir=seals, placebo_draws=20)
    assert json.dumps(cs._clean(res), sort_keys=True) == json.dumps(cs._clean(res2), sort_keys=True)  # deterministic
    # a modified file breaks verification
    pd.DataFrame({"ts": [1.0]}).to_csv(run / "trades" / "1000.csv.gz", index=False)
    with pytest.raises(cs.SealUnavailableError):
        cs.run_ladders_r1(run, n_boot=50, decl_sha="d", job="t", min_ladders=1, seals_dir=seals)


def test_ladders_below_min_ladders_not_testable_and_counted(tmp_path):
    run = make_run(tmp_path, n_lad=5)
    seal = h5_seal.seal_run(run, trials_path=tmp_path / "t.jsonl", allow_incomplete=True)
    seals = tmp_path / "s"
    seals.mkdir()
    (seals / "h5_cb1_ladders_SEAL.json").write_text(json.dumps({"listing_sha256": seal["listing_sha256"]}))
    res = cs.run_ladders_r1(run, n_boot=20, decl_sha="d", job="t", seals_dir=seals)
    assert res["not_testable"] and res["tests"]["B1"]["p"] == 1.0 and res["tests"]["B2"]["advance"] is False


def test_missing_progress_flag_is_treated_truncated(tmp_path):
    run = make_run(tmp_path, n_lad=2)
    assert cs.load_trade_flags(run)["1000"] is False
    (run / "progress.jsonl").unlink()
    with pytest.raises(forecast.ArchivedDataError):
        cs.load_trade_flags(run)


def test_breakeven_placebo_rarely_advances():
    rng = np.random.default_rng(5)
    n = 300
    K = np.full(n, 0.72)
    u = pd.DataFrame({"K": K, "d": np.full(n, 30.0), "event_id": [f"e{i % 150}" for i in range(n)],
                      "week": [f"w{i % 10}" for i in range(n)], "net": rng.random(n)})
    p = cs.breakeven_placebo(u, floor=0.01, alpha=0.01, draws=100, n_boot=20)
    assert p["advance_rate"] <= cs.PLACEBO_MAX_ADVANCE_RATE and p["calibrated"]


# ---------------------------------------------------------------------------------------------
# B3 prospective pieces
# ---------------------------------------------------------------------------------------------


def test_rung_list_immutable_and_hash_checked(tmp_path):
    ev = [{"id": "1", "title": "t", "negRisk": False, "startDate": "2026-09-01T00:00:00Z", "markets": [
        {"id": "10", "question": "Will X happen by December 31, 2026?", "groupItemTitle": "December 31",
         "clobTokenIds": '["a","b"]', "createdAt": "2026-09-01T00:00:00Z"},
        {"id": "11", "question": "Will X happen by November 30, 2026?", "groupItemTitle": "November 30",
         "clobTokenIds": '["c","d"]', "createdAt": "2026-09-01T00:00:00Z"}]}]
    doc = cs.build_rung_list(ev, "2026-10-19T00:00:00Z", "2026-12-31")
    assert doc["n_ladders"] == 1 and all("outcome_prices" not in r for r in doc["ladders"][0]["rungs"])
    assert doc["ladders"][0]["ifh2_period"] is False or doc["ladders"][0]["ifh2_period"] is True
    p = tmp_path / "rl.json"
    sha = cs.write_rung_list(doc, p)
    with pytest.raises(cs.RungListError):
        cs.write_rung_list(doc, p)
    assert cs.load_rung_list(p, sha)["sha256"] == sha
    with pytest.raises(cs.RungListError):
        cs.load_rung_list(p, "0" * 64)
    p.write_bytes(p.read_bytes() + b" ")
    with pytest.raises(cs.RungListError):
        cs.load_rung_list(p)


def _rl():
    rs = [{"market_id": "10", "deadline": cs._ep("2026-11-15T00:00:00Z"), "in_window": True},
          {"market_id": "11", "deadline": cs._ep("2026-12-15T00:00:00Z"), "in_window": True}]
    return {"deadline_max": "2026-12-31", "ladders": [{"ladder_id": "1:x", "event_id": "1", "ifh2_period": False, "rungs": rs}]}


def _rung_rows(t0, n, near_bid=0.30, near_ask=0.34, cid0=0):
    rows = []
    for j in range(n):
        t = t0 + j * 2 * H
        for mid, bid, ask in (("10", near_bid, near_ask), ("11", 0.40, 0.44)):
            rows.append({"capture_id": f"r{cid0 + j}", "cs": t, "market_id": mid, "best_bid": bid, "best_ask": ask,
                         "last_trade_price": 0.33, "closed": "False", "accepting_orders": 1.0, "volume_num": 10.0,
                         "fee_category": "politics"})
    return pd.DataFrame(rows)


def test_prospective_rungs_first_capture_recorded_ask_and_censoring():
    t0 = cs._ep("2026-10-20T00:00:00Z")
    rows = _rung_rows(t0, 3)
    out = {"10": {"final_yes": 0.0, "closed_time": "2026-11-16T00:00:00Z"}}
    u = cs.prospective_rungs(rows, _rl(), outcomes=out)
    assert len(u) == 1 and u.iloc[0]["t"] == t0 and u.iloc[0]["a"] == pytest.approx(0.70)  # 1 - best_bid at the FIRST capture
    assert u.iloc[0]["net"] == pytest.approx(1.0 - 0.70 - u.iloc[0]["f"]) and u.iloc[0]["status"] == "resolved"
    assert u.iloc[0]["week"] == pd.Timestamp(cs._ep("2026-11-15T00:00:00Z"), unit="s", tz="UTC").strftime("%G-W%V")
    # unresolved with a passed deadline -> censored at the last extracted NO bid (1 - best_ask), flagged
    u2 = cs.prospective_rungs(rows, _rl(), outcomes={})
    assert u2.iloc[0]["censored"] and u2.iloc[0]["net"] == pytest.approx((1.0 - 0.34) - 0.70 - u2.iloc[0]["f"])
    # resolved only AFTER the censor date counts as unresolved
    u3 = cs.prospective_rungs(rows, _rl(), outcomes={"10": {"final_yes": 0.0, "closed_time": "2027-03-01T00:00:00Z"}})
    assert u3.iloc[0]["censored"]
    # v1 outside [0.05, 0.60] or the ladder inconsistent -> no unit
    assert len(cs.prospective_rungs(_rung_rows(t0, 2, 0.70, 0.74), _rl(), outcomes=out)) == 0


def test_b3_read_date_guards():
    with pytest.raises(cs.TooEarlyError):
        cs.check_b3_read_date(datetime(2026, 12, 1, tzinfo=UTC))
    with pytest.raises(cs.TooEarlyError):
        cs.check_b3_read_date(datetime(2027, 1, 10, tzinfo=UTC))  # counted run before T_censor_B3
    cs.check_b3_read_date(datetime(2027, 1, 10, tzinfo=UTC), interim=True)
    cs.check_b3_read_date(datetime(2027, 2, 1, tzinfo=UTC))


def test_survivorship_label():
    r = pd.DataFrame({"in_walk": [True] * 8 + [False] * 2, "yes_final": [0.0] * 8 + [1.0, 1.0], "net": 0.0})
    s = cs.survivorship_check(r)
    assert s["share_missing"] == 0.2 and s["listing_survivorship_biased"] is True
    assert cs.survivorship_check(r.iloc[:0]) == {"checked": False}


def test_b3_tests_censoring_flag_and_no_units():
    assert cs.b3_tests(pd.DataFrame(), n_boot=10)["tests"]["B3"]["testable"] is False
    rng = np.random.default_rng(2)
    n = 150
    a = np.full(n, 0.70)
    yes = (rng.random(n) < 0.3).astype(float)
    u = pd.DataFrame({"event_id": [f"e{i}" for i in range(n)], "week": [f"w{i % 8}" for i in range(n)],
                      "a": a, "f": 0.005, "K": a + 0.005, "d": 30.0, "net": (1 - yes) - a - 0.005,
                      "censored": np.arange(n) < 30, "ifh2_period": False, "sweep_ok": False,
                      "a_sweep": np.nan, "yes_final": yes})
    res = cs.b3_tests(u, n_boot=50, placebo_draws=20)
    t = res["tests"]["B3"]
    assert t["resolution_lag_sensitive"] is True and t["censored_share"] == pytest.approx(0.2)
    assert set(res["sensitivities"]) == {"censored_at_0", "censored_at_1"}


def test_committed_listing_hash_one_file_format_only(tmp_path):
    (tmp_path / "h5_cb1_ladders_SEAL.json").write_text(json.dumps({"listing_sha256": "ab"}))
    assert cs.committed_listing_hash("h5_cb1_ladders", tmp_path) == "ab"
    with pytest.raises(cs.SealUnavailableError):
        cs.committed_listing_hash("other", tmp_path)
    # combined / nested layouts are no longer accepted
    (tmp_path / "h5_cb1_SEAL.json").write_text(json.dumps({"runs": {"h5_cb1_ladders": {"listing_sha256": "ab"}}}))
    with pytest.raises(cs.SealUnavailableError):
        cs.committed_listing_hash("h5_cb1", tmp_path)
    (tmp_path / "h5_cb1_SEAL.json").write_text(json.dumps({"runs": [{"run_id": "h5_cb1", "listing_sha256": "cd"}]}))
    with pytest.raises(cs.SealUnavailableError):
        cs.committed_listing_hash("h5_cb1", tmp_path)
    (tmp_path / "h5_cb1_SEAL.json").write_text("not json")
    with pytest.raises(cs.SealUnavailableError):
        cs.committed_listing_hash("h5_cb1", tmp_path)


def test_non_single_winner_share_is_per_event_not_per_trigger():
    n_ev, per = 40, 3
    rows = []
    for e in range(n_ev):
        for k in range(per):
            rows.append({"gid": f"G{e}", "capture_id": f"c{k}", "day": f"2026-10-{12 + k}", "C": 0.9, "executed": True,
                         "net": 0.1, "K": 0.9, "d": 5.0, "n_legs": 3, "sweep_ok": True, "net_sweep": 0.1, "resolved": True,
                         "net_real": 0.1, "single_winner": not (e == 0 and k == 0)})
    trig = pd.DataFrame(rows)
    ec = pd.DataFrame({"gid": [f"G{e}" for e in range(n_ev)], "day": "2026-10-12", "U": 1.0, "O": 0.0})
    real = cs.negrisk_tests(ec, trig, n_boot=20, dev=False, alpha=0.05)["D2"]["realised"]
    # 1 of 120 triggers (0.8%) would pass a per-trigger 2% ceiling; 1 of 40 events (2.5%) does not
    assert real["non_single_winner_share"] == pytest.approx(1 / 40) and real["ceiling_ok"] is False


def test_event_members_are_read_as_of_the_capture(tmp_path):
    caps, members = many_events(2, 2)
    make_extract(tmp_path, caps, members)  # all counts fetched 2026-01-01
    base = pd.read_csv(tmp_path / "event_members.csv.gz", compression="gzip")
    late = pd.DataFrame({"neg_risk_market_id": ["G0", "Gnew"], "member_count": [99, 3],
                         "fetched_utc": [iso(T0 + 3600), iso(T0 + 3600)]})
    pd.concat([base, late]).to_csv(tmp_path / "event_members.csv.gz", index=False)
    before = cs.load_event_members(tmp_path, iso(T0))
    assert before["G0"] == 3 and "Gnew" not in before  # the later refresh and the new id are not yet known
    after = cs.load_event_members(tmp_path, iso(T0 + 7200))
    assert after["G0"] == 99 and after["Gnew"] == 3
    # eligibility per capture: c00 (T0) sees count 3 (eligible); c01 (T0+2h) sees 99 (mismatch)
    df = pd.concat([pd.DataFrame(r).assign(cs=t, capture_id=c) for c, t, r in caps], ignore_index=True)
    ec, cnt = cs.negrisk_event_captures(df[df["neg_risk_market_id"] == "G0"], cs.members_asof_loader(tmp_path))
    assert list(ec["capture_id"]) == ["c00"] and cnt["ineligible_reasons"]["member_count_mismatch"] == 1
    # an id first fetched after the capture is absent (no_member_count), never back-filled
    g = pd.DataFrame(_event_rows("c00", T0, "Gnew", [0.3, 0.3, 0.3])).assign(cs=T0, capture_id="c00")
    assert cs.negrisk_event_captures(g, cs.members_asof_loader(tmp_path))[1]["ineligible_reasons"] == {"no_member_count": 1}


def test_member_count_asof_else_first_fetch_with_lag_and_sensitivity(tmp_path):
    caps, members = many_events(2, 2)
    make_extract(tmp_path, caps, members)  # G0/G1 fetched 2026-01-01 (as-of for every capture)
    late = pd.DataFrame({"neg_risk_market_id": ["Gnew", "Gnew", "Gnone"], "member_count": [3, 3, 3],
                         "fetched_utc": [iso(T0 + 5 * 3600), iso(T0 + 9 * 3600), iso(T0 + 9 * 3600)]})
    base = pd.read_csv(tmp_path / "event_members.csv.gz", compression="gzip")
    pd.concat([base, late]).to_csv(tmp_path / "event_members.csv.gz", index=False)
    ff = cs.load_first_fetch(tmp_path)
    assert ff["Gnew"] == (3, cs._ep(iso(T0 + 5 * 3600))) and ff["G0"][0] == 3  # first row, not the later refresh
    g = pd.DataFrame(_event_rows("c00", T0, "Gnew", [0.3, 0.3, 0.3])).assign(cs=T0, capture_id="c00")
    g2 = pd.DataFrame(_event_rows("c00", T0, "G0", [0.3, 0.3, 0.3])).assign(cs=T0, capture_id="c00")
    g3 = pd.DataFrame(_event_rows("c00", T0, "Gnone2", [0.3, 0.3, 0.3])).assign(cs=T0, capture_id="c00")
    df = pd.concat([g, g2, g3], ignore_index=True)
    ec, cnt = cs.negrisk_event_captures(df, cs.members_asof_loader(tmp_path), first_fetch=ff)
    by = ec.set_index("gid")
    assert by.loc["Gnew", "member_count_source"] == "first_fetch" and by.loc["Gnew", "member_count_lag_h"] == pytest.approx(5.0)
    assert by.loc["G0", "member_count_source"] == "asof" and math.isnan(by.loc["G0", "member_count_lag_h"])
    assert cnt["member_count_source_all_groups"] == {"asof": 1, "first_fetch": 1, "none": 1}
    assert cnt["member_count_source_eligible"] == {"asof": 1, "first_fetch": 1}
    assert cnt["member_count_lag_h_first_fetch"]["max"] == pytest.approx(5.0)
    assert cnt["ineligible_reasons"]["no_member_count"] == 1
    # sensitivity: as-of only drops the first_fetch event-capture
    ec2, cnt2 = cs.negrisk_event_captures(df, cs.members_asof_loader(tmp_path), first_fetch=ff, asof_only=True)
    assert list(ec2["gid"]) == ["G0"] and cnt2["member_count_source_all_groups"] == {"asof": 1, "first_fetch": 0, "none": 2}
    # build/census carry the source counts; run_negrisk reports the as-of-only sensitivity
    c8, m8 = many_events(8, 4)
    make_extract(tmp_path / "x", c8, m8)
    cl = cs.load_capture_list(tmp_path / "x" / "capture_lists" / "dev.json", window="dev")
    b = cs.build_negrisk(tmp_path / "x", cl, "dev")
    assert b["counts"]["event_captures"]["member_count_source_eligible"]["asof"] == len(b["ec"])
    res = cs.run_negrisk(tmp_path / "x", cl, "dev", n_boot=50, dev=True, alpha=0.01, placebo_draws=5)
    assert set(res["sensitivity_asof_only"]["tests"]) == {"D1", "D2"}


def test_d_declaration_carries_member_count_and_family_rules():
    d = cs.declaration()
    assert "first-fetched" in d["D"]["member_count_rule"] and "sensitivity_asof_only" in d["D"]["member_count_rule"]
    assert "p = 1" in d["batch_holm_family"] and "B1 and B2" in d["batch_holm_family"]


# ---------------------------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------------------------


def _runner():
    import importlib.util

    spec = importlib.util.spec_from_file_location("run_cb1_structural", Path(__file__).resolve().parents[2] / "scripts" / "run_cb1_structural.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_runner_census_is_uncounted_and_counted_run_refuses_without_declaration(tmp_path, monkeypatch, capsys):
    caps, members = many_events(10, 3)
    doc = make_extract(tmp_path, caps, members)
    r = _runner()
    assert r.main(["census-D", "--window", "dev", "--extract-root", str(tmp_path)]) == 0
    out = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert out["counts_only"] and out["n_event_clusters"] == 10 and out["list_sha256"] == doc["sha256"]

    def _refuse(*a, **k):
        raise cs.DeclarationError("no committed declaration")
    monkeypatch.setattr(cs, "require_declaration", _refuse)
    monkeypatch.setattr(provenance, "TRIALS_PATH", tmp_path / "never.jsonl")
    assert r.main(["snapshots", "--family", "D", "--window", "dev", "--extract-root", str(tmp_path),
                   "--list-sha256", doc["sha256"]]) == 3
    assert json.loads(capsys.readouterr().out.strip().splitlines()[-1])["refused"] == "DeclarationError"
    assert not (tmp_path / "never.jsonl").exists()


def test_runner_refuses_h3_power(monkeypatch):
    monkeypatch.setattr(cs, "require_declaration", lambda *a, **k: "d")
    with pytest.raises(SystemExit):
        _runner().main(["ladders", "--run-id", "h3_power"])


def test_runner_pin_rep_start_and_rung_list_and_fetch_outcomes_guards(tmp_path, monkeypatch, capsys):
    r = _runner()
    f = tmp_path / "pin.json"
    monkeypatch.setattr(cs, "T_REP_START_FILE", f)
    monkeypatch.setattr(r, "_git_commit_time", lambda sha: "2026-10-20T10:00:00+01:00")
    assert r.main(["pin-rep-start", "--freeze-commit", "abc1234"]) == 0
    assert json.loads(f.read_text())["t_rep_start"] == "2026-10-20T11:00:00Z"
    assert r.main(["pin-rep-start", "--freeze-commit", "abc1234"]) == 3  # pinned once
    with pytest.raises(SystemExit):  # --as-of must equal the pin
        r.main(["rung-list", "--as-of", "2026-10-21T00:00:00Z", "--out", str(tmp_path / "rl.json")])
    capsys.readouterr()

    # fetch-outcomes-D: the committed declaration is required BEFORE any download
    def _refuse(*a, **k):
        raise cs.DeclarationError("no committed declaration")

    def _no_network(*a, **k):
        raise AssertionError("network touched before the declaration check")

    from astrolabe.research_lab import history_backfill as hb
    monkeypatch.setattr(cs, "require_declaration", _refuse)
    monkeypatch.setattr(hb, "httpx_transport", _no_network)
    monkeypatch.setattr(cs, "fetch_outcomes", _no_network)
    assert r.main(["fetch-outcomes-D", "--window", "dev", "--extract-root", str(tmp_path), "--out", str(tmp_path / "o.csv")]) == 3
    assert json.loads(capsys.readouterr().out.strip().splitlines()[-1])["refused"] == "DeclarationError"


# ---------------------------------------------------------------------------------------------
# streaming / pruned window loader (q0022a OOM): identical results, declaration unchanged
# ---------------------------------------------------------------------------------------------


def _full_load(monkeypatch):
    """Reference path: the pre-fix loader (all columns, no interning)."""
    orig = cs.load_window_captures
    monkeypatch.setattr(cs, "load_window_captures",
                        lambda *a, columns=None, **k: orig(*a, **k))


def _loader_world(tmp_path):
    caps, members = many_events(30, 6, persistent_cheap)
    # a closed (resolved) member with a final outcome and an event with an open-member NaN quote
    caps[1][2][0].update({"closed": "True", "final_yes": 0.0})
    caps[2][2][3].update({"best_ask": np.nan})
    make_extract(tmp_path, caps, members)
    return cs.load_capture_list(tmp_path / "capture_lists" / "dev.json", window="dev")


def test_pruned_loader_frames_equal_on_used_columns(tmp_path):
    cl = _loader_world(tmp_path)
    full, cs1, c1 = cs.load_window_captures(tmp_path, cl, "dev")
    pr, cs2, c2 = cs.load_window_captures(tmp_path, cl, "dev", columns=cs.D_NEGRISK_COLS)
    assert cs1 == cs2 and c1 == c2
    assert set(pr.columns) == set(cs.D_NEGRISK_COLS) | {"cs", "capture_id"}
    pd.testing.assert_frame_equal(full[pr.columns].reset_index(drop=True), pr.reset_index(drop=True))


def test_window_market_ids_streaming_equals_full_load(tmp_path):
    cl = _loader_world(tmp_path)
    full, _, _ = cs.load_window_captures(tmp_path, cl, "dev")
    assert cs.window_market_ids(tmp_path, cl, "dev") == sorted(set(full["market_id"].astype(str)))


def test_window_market_ids_streaming_still_validates(tmp_path):
    cl = _loader_world(tmp_path)
    (tmp_path / "negrisk" / "c02.csv.gz").unlink()
    with pytest.raises(cs.forecast.ArchivedDataError):
        cs.window_market_ids(tmp_path, cl, "dev")


def test_build_and_run_negrisk_identical_with_pruned_loader(tmp_path, monkeypatch):
    cl = _loader_world(tmp_path)
    outcomes = {"G0m1": 0.0}
    new_b = cs.build_negrisk(tmp_path, cl, "dev", outcomes=outcomes)
    new_r = cs.run_negrisk(tmp_path, cl, "dev", n_boot=50, dev=True, alpha=0.01, placebo_draws=10,
                           outcomes=outcomes)
    _full_load(monkeypatch)
    old_b = cs.build_negrisk(tmp_path, cl, "dev", outcomes=outcomes)
    old_r = cs.run_negrisk(tmp_path, cl, "dev", n_boot=50, dev=True, alpha=0.01, placebo_draws=10,
                           outcomes=outcomes)
    assert cs.census_negrisk(new_b) == cs.census_negrisk(old_b)
    pd.testing.assert_frame_equal(new_b["ec"], old_b["ec"])
    pd.testing.assert_frame_equal(new_b["trig"], old_b["trig"])
    assert json.dumps(cs._clean(new_r), sort_keys=True) == json.dumps(cs._clean(old_r), sort_keys=True)


def test_declaration_hash_matches_committed_record():
    rec = json.loads((Path(__file__).resolve().parents[3] / "docs/research_lab/seals/cb1_structural_DECLARATION.json")
                     .read_text())
    assert cs.declaration_sha256() == rec["declaration_sha256"]
