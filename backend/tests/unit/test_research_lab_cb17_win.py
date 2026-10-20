# ruff: noqa: E501
"""CB17 window code (synthetic data only): the code-freeze and T17_rules records, the field-restricted readers and their refusals, the frames of B / C / E on a synthetic world, the
inference engine, the counted lines and the smoke fixtures. No real window file is opened anywhere here."""

from __future__ import annotations

import json
import math
from collections import Counter

import numpy as np
import pytest

from astrolabe.research_lab import cb16_common as c16
from astrolabe.research_lab import cb17_b as fb
from astrolabe.research_lab import cb17_c as fc
from astrolabe.research_lab import cb17_common as c17
from astrolabe.research_lab import cb17_e as fe
from astrolabe.research_lab import cb17_smoke as sm
from astrolabe.research_lab import cb17_wcommon as w
from astrolabe.research_lab import cb17_win as win
from tests.cb17_synth import ep, print_, stamp, write_capture, write_day
from tests.cb17_wsynth import FLOOR, H, world, write_records

DAY = 86400.0
Refused, NotNow = c17.Refused, c17.NotNow


@pytest.fixture(scope="module")
def rules(tmp_path_factory):
    p = tmp_path_factory.mktemp("cb17r") / "rules.json"
    c17.write_rules(p)
    return p


# ---- records: code freeze, T17_rules, results copy ----------------------------------------------------------------------------------------------------


def test_code_pin_covers_every_window_module_and_the_runner():
    src = win.code_sources()
    assert set(src["files"]) == {f"{m}.py" for m in win.CODE_MODULES} | {"run_cb17.py"} and "cb17_jobs" in win.CODE_MODULES
    assert all(len(v) == 64 for v in src["files"].values()) and win.code_sha256() == win.code_sha256()


def test_code_freeze_record_pins_this_code_the_rules_parts_and_the_attestation(tmp_path, rules):
    shas = win.verify_parts(rules, require_committed=False)
    rec = write_records(tmp_path, rules=rules, code_sha=win.code_sha256(), shas=shas)
    ok = win.require_code_freeze(rec["freeze"], rules_shas=shas, require_committed=False)
    assert ok["code_sha256"] == win.code_sha256() and ok["frozen_utc"]
    (tmp_path / "b").mkdir()
    bad = write_records(tmp_path / "b", rules=rules, code_sha="0" * 64, shas=shas)
    with pytest.raises(Refused, match="does not cover"):
        win.require_code_freeze(bad["freeze"], rules_shas=shas, require_committed=False)
    other = {**shas, "B": "1" * 64}
    with pytest.raises(Refused, match="other rules parts"):
        win.require_code_freeze(rec["freeze"], rules_shas=other, require_committed=False)
    (tmp_path / "c").mkdir()
    noatt = write_records(tmp_path / "c", rules=rules, code_sha=win.code_sha256(), shas=shas, attestation="")
    with pytest.raises(Refused, match="attestation"):
        win.require_code_freeze(noatt["freeze"], rules_shas=shas, require_committed=False)
    assert win.require_code_freeze(noatt["freeze"], rules_shas=shas, require_committed=False, need_attestation=False)["frozen_utc"]
    with pytest.raises(Refused, match="not found"):
        win.require_code_freeze(tmp_path / "missing.json", rules_shas=shas, require_committed=False)


def test_uncommitted_records_are_refused_under_the_default(tmp_path, rules):
    shas = win.verify_parts(rules, require_committed=False)
    rec = write_records(tmp_path, rules=rules, code_sha=win.code_sha256(), shas=shas)
    for fn, p in ((win.require_code_freeze, rec["freeze"]), (win.require_t17, rec["t17"])):
        with pytest.raises(Refused):
            fn(p, rules_shas=shas)  # require_committed defaults to True: a tmp file is not tracked by git


def test_t17_record_gives_s8_at_the_floor_and_slides_only_after_25_october(tmp_path, rules):
    shas = win.verify_parts(rules, require_committed=False)
    early = write_records(tmp_path, rules=rules, code_sha="x", shas=shas, t17_utc="2026-10-25T00:00:00Z")
    assert win.require_t17(early["t17"], rules_shas=shas, require_committed=False)["s8"] == FLOOR
    (tmp_path / "l").mkdir()
    late = write_records(tmp_path / "l", rules=rules, code_sha="x", shas=shas, t17_utc="2026-10-26T06:00:00Z")
    t = win.require_t17(late["t17"], rules_shas=shas, require_committed=False)
    assert t["s8"] == FLOOR + 2 * DAY and t["s8_utc"] == "2026-10-28T00:00:00Z"
    assert w.s8_from_rules(ep("2026-10-20T00:00:00Z")) == FLOOR  # never before the floor
    bad = json.loads(early["t17"].read_text())
    bad["parts"]["B"] = "2" * 64
    early["t17"].write_text(json.dumps(bad))
    with pytest.raises(Refused, match="other rules parts"):
        win.require_t17(early["t17"], rules_shas=shas, require_committed=False)


def test_rep_rows_stay_closed_until_the_screen_result_and_its_committed_copy_exist(tmp_path):
    root, seals = tmp_path / "creative_batch17", tmp_path / "seals"
    root.mkdir()
    seals.mkdir()
    with pytest.raises(NotNow, match="results_8.json missing"):
        win.require_results_copy(root, seals, require_committed=False)
    (root / "results_8.json").write_text('{"x": 1}')
    with pytest.raises(NotNow, match="committed copy"):
        win.require_results_copy(root, seals, require_committed=False)
    (seals / win.RESULTS_COPY_NAME).write_text('{"x": 2}')
    with pytest.raises(NotNow, match="differs"):
        win.require_results_copy(root, seals, require_committed=False)
    (seals / win.RESULTS_COPY_NAME).write_text('{"x": 1}')
    assert win.require_results_copy(root, seals, require_committed=False) == {"x": 1}
    with pytest.raises(NotNow, match="not committed"):
        win.require_results_copy(root, seals, require_committed=True)  # a tmp file is untracked
    s8 = FLOOR
    lo = w.windows8(s8)["rep"]["units"][0]
    with pytest.raises(Refused, match="REP_8"):
        w.guard_rep_unit(lo + 1, s8, rep_open=False)
    assert w.guard_rep_unit(lo - 1, s8, rep_open=False) == lo - 1 and w.guard_rep_unit(lo + 1, s8, rep_open=True) == lo + 1


# ---- readers: the lookback floor, refused roots, forbidden fields -------------------------------------------------------------------------------------


def test_no_window_reader_opens_a_directory_or_row_before_the_floor(tmp_path):
    snap = tmp_path / "snapshots"
    write_capture(snap, FLOOR - 3 * H, [{"mid": "1", "cid": "c1", "eid": "E1", "bid": "0.48", "ask": "0.50"}])
    for lo in (FLOOR - 6 * H, FLOOR - 3 * H, FLOOR - 2 * H, FLOOR - 1.0):
        with pytest.raises(Refused, match="lookback floor"):
            win.list_window_dirs(snap, "snapshots", c17.CAPTURE_DIR_RE, lo, FLOOR + H, Counter())
        with pytest.raises(Refused, match="lookback floor"):
            win.list_captures(snap, lo, FLOOR + H, Counter())
    # at the floor the pre-floor directory is simply not listed (and not opened: it holds garbage)
    junk = snap / stamp(FLOOR - 600.0, "bad00bad")
    junk.mkdir(parents=True)
    (junk / "rows.csv.gz").write_bytes(b"not gzip")
    stats: Counter = Counter()
    assert win.list_window_dirs(snap, "snapshots", c17.CAPTURE_DIR_RE, FLOOR, FLOOR + H, stats) == [] and stats["snapshots_dirs_before_read_window_not_opened"] == 2
    with pytest.raises(Refused, match="lookback floor"):
        list(win.iter_monitor(tmp_path / "live_trades", FLOOR - 1.0, FLOOR + H, Counter()))
    d = write_capture(snap, FLOOR + 600.0, [{"mid": "1", "cid": "c1", "eid": "E1", "bid": "0.48", "ask": "0.50", "recv": FLOOR - 5.0}])
    with pytest.raises(Refused, match="before the lookback floor"):
        list(win.iter_rows(d / "rows.csv.gz", ("market_id",), c17.CAPTURE_FIELDS, "received_utc"))


def test_window_readers_refuse_roots_and_never_decode_forbidden_fields(tmp_path):
    for root in w.WINDOW_REFUSED_ROOTS:
        with pytest.raises(Refused):
            win.refuse_window_path(tmp_path / "research_lab" / root / "f.csv.gz", ())
    tr = tmp_path / "live_trades"
    ts = FLOOR + 100.0
    write_day(tr, "20261026", [print_(ts, "c1", 0.4, side="BUY", tx="t1", mkt="m1"), print_(FLOOR - 50.0, "c9", 0.4, tx="t2")])
    (tr / "scores-20261026.jsonl").write_text("{}\n")
    got = list(win.iter_monitor(tr, FLOOR, FLOOR + H, Counter()))
    assert got == [(ts, "c1", "m1")]  # side, recv_ts, key, wallet never reach the tuple; the pre-floor print is outside [lo, hi)
    pr = list(fe.iter_prints(tr, FLOOR, FLOOR + H, Counter()))
    assert len(pr) == 1 and not ({"side", "recv_ts", "key", "wallet_hash"} & set(pr[0]))
    d = write_capture(tmp_path / "snapshots", FLOOR + 600.0, [{"mid": "1", "cid": "c1", "eid": "E1", "bid": "0.48", "ask": "0.50"}])
    for bad in ("chg_1h", "last_trade_price", "outcome_prices"):
        with pytest.raises(Refused, match="not whitelisted"):
            list(win.iter_rows(d / "rows.csv.gz", (bad,), c17.CAPTURE_FIELDS, "received_utc"))


def test_the_smoke_fixture_checks_all_pass_and_a_missing_worn_file_is_a_refusal(tmp_path):
    ref = sm.check_refusals(tmp_path / "a")
    rul = sm.check_rules_fixtures(tmp_path / "b")
    assert all(ref.values()) and all(rul.values()), (ref, rul)
    assert set(ref) | set(rul) | {"parts_verify", "pins_cb13", "pins_cb16", "reproduce_P1", "reproduce_P2", "reproduce_P3"} == set(w.SMOKE_CRITERIA)
    with pytest.raises(Refused):
        sm.probe_p1(tmp_path / "nofills", tmp_path / "live_trades", tmp_path / "snapshots")
    with pytest.raises(Refused):
        sm.probe_p2(tmp_path / "nosweeps", tmp_path / "snapshots")
    with pytest.raises(Refused):
        sm.probe_p3(tmp_path / "nosnapshots")
    assert sm.compare({"a": 1, "b": 2}, {"a": 1, "b": 3})["pass"] is False and sm.compare({"a": 1}, {"a": 1})["pass"] is True


def test_the_pinned_cb13_cb16_functions_are_unchanged_and_the_smoke_needs_map_every_family():
    assert w.pins_ok()["ok"] is True
    assert set(w.SMOKE_NEEDS) == {"B", "C", "E"} and set(w.SMOKE_NEEDS["B"]) | set(w.SMOKE_NEEDS["C"]) | set(w.SMOKE_NEEDS["E"]) <= set(w.SMOKE_CRITERIA)
    assert "reproduce_P2" in w.SMOKE_NEEDS["B"] and "reproduce_P3" in w.SMOKE_NEEDS["C"] and "reproduce_P1" in w.SMOKE_NEEDS["E"]
    # the exact P1-P3 counts of section 0.3 are declared verbatim in the smoke
    assert sm.P1_EXPECTED["fills"] == 2931 and sm.P1_EXPECTED["open"] == 676 and sm.P2_EXPECTED["hash_diff"] == 139880 and sm.P3_EXPECTED["events_ge6"] == 1226


# ---- frames on a synthetic world -----------------------------------------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def synth(tmp_path_factory):
    root = tmp_path_factory.mktemp("cb17f")
    return {"root": root, "w": world(root, FLOOR, n_events=14, members=2, n_passes=30)}


def _b(synth, arm, **kw):
    W = synth["w"]
    return fb.build_frame(W["sw"], W["snap"], W["tr"], units=(FLOOR, FLOOR + 14 * DAY), read_lo=FLOOR, marks_hi=FLOOR + 14 * DAY + 8 * H, arm=arm, **kw)


def test_event_arms_are_disjoint_and_cover_the_sweep_universe(synth):
    f0, f1 = _b(synth, 0), _b(synth, 1)
    t0 = {f0["vocab"]["tok"][i] for i in f0["arrays"]["tok"]}
    t1 = {f1["vocab"]["tok"][i] for i in f1["arrays"]["tok"]}
    assert t0 and t1 and not (t0 & t1) and len(t0) + len(t1) == 28
    assert f0["stats"]["other_arm_token_passes"] == len(f1["arrays"]["tok"]) and f1["stats"]["other_arm_token_passes"] == len(f0["arrays"]["tok"])


def test_b_frame_labels_floor_units_stamp_semantics_and_never_stores_a_mark_value(synth):
    f = _b(synth, 0)
    a = f["arrays"]
    assert f["stats"]["lpre_unavailable_lookback_floor"] >= 1  # the first pass at the floor has no previous pass: counted, never back-filled
    assert f["gbt"]["hash_same"] == f["gbt"]["hash_same_stamp_same"] and f["gbt"]["hash_changed"] == f["gbt"]["hash_changed_stamp_changed"]  # the synthetic stamp semantics
    assert not ({"side", "wallet", "mark", "outcome"} & set(a)) and a["mk2_1"].dtype == np.int16  # pass indices and statuses only
    assert set(np.unique(a["state"])) <= {0, 1, 2}
    f2 = _b(synth, 0)
    assert all(np.array_equal(a[k], f2["arrays"][k], equal_nan=True) for k in a)  # deterministic


def test_b_frame_stops_on_its_budget_and_never_reads_before_the_floor(synth):
    with pytest.raises(NotNow, match="budget"):
        _b(synth, 0, budget_s=-1.0)
    W = synth["w"]
    with pytest.raises(Refused, match="lookback floor"):
        fb.build_frame(W["sw"], W["snap"], None, units=(FLOOR, FLOOR + DAY), read_lo=FLOOR - 2 * H, marks_hi=FLOOR + DAY, arm=0)


def test_frames_roundtrip_through_write_once_files_and_carry_no_forbidden_column(synth, tmp_path):
    f = _b(synth, 0)
    out = tmp_path / "creative_batch17" / "screen" / "bc"
    files = fb.write_frame(out, f)
    assert all(p.exists() for p in files)
    L = fb.load_frame(out)
    assert all(np.array_equal(L[k], f["arrays"][k], equal_nan=True) for k in f["arrays"]) and L["_meta"]["n_passes"] == f["n_passes"]
    with pytest.raises(Refused, match="written once"):
        fb.write_frame(out, f)
    with pytest.raises(Refused):
        win.write_arrays(tmp_path / "elsewhere" / "x.npz", {"a": np.zeros(1)})
    with pytest.raises(Refused, match="forbidden"):
        win.write_arrays(tmp_path / "creative_batch17" / "y.npz", {"wallet_hash": np.zeros(1)})


def test_c_frame_uses_only_k_minus_1_and_k_for_eligibility_and_marks_are_statuses(synth, tmp_path):
    W = synth["w"]
    fr = fc.build_frame(W["snap"], units=(FLOOR, FLOOR + 14 * DAY), read_lo=FLOOR, marks_hi=FLOOR + 14 * DAY + 8 * H, arm=0)
    U, M = fr["units"], fr["members"]
    assert len(U["ev"]) > 0 and set(np.unique(U["cls"])) <= {0, 1, 2} and (U["cap"] >= 6).all()  # >= 6 prior traded intervals: trailing terciles
    assert set(np.unique(M["st1"])) <= set(fc.REASON_CODE.values())
    assert not ({"b1", "a1", "mk", "mark"} & set(M)) and fr["gcu"]["traded"] >= fr["gcu"]["oi_changed"]
    out = tmp_path / "creative_batch17" / "bc"
    fc.write_frame(out, fr)
    L = fc.load_frame(out)
    assert np.array_equal(L["U"]["r"], U["r"], equal_nan=True) and L["M"]["unit"].shape == M["unit"].shape
    with pytest.raises(Refused, match="lookback floor"):
        fc.build_frame(W["snap"], units=(FLOOR, FLOOR + DAY), read_lo=FLOOR - 6 * H, marks_hi=FLOOR + DAY, arm=0)
    with pytest.raises(NotNow, match="budget"):
        fc.build_frame(W["snap"], units=(FLOOR, FLOOR + 14 * DAY), read_lo=FLOOR, marks_hi=FLOOR + 14 * DAY + 8 * H, arm=0, budget_s=-1.0)


def test_e_frame_has_no_side_and_the_census_reports_both_populations_with_k_zero(synth):
    W = synth["w"]
    fr = fe.build_frame(W["tr"], W["snap"], units=(FLOOR, FLOOR + 14 * DAY), cap_lo=FLOOR)
    assert fr["transactions"] > 0 and all("side" not in r and "recv_ts" not in r for r in fr["rows"])
    cen = fe.census(fr)
    assert cen["k"] == 0 and set(cen["populations"]) == {"counts", "mde", "rule"} and "reentry" in cen
    c17.assert_clean_result(cen)


def test_census_blocks_are_counts_and_standard_errors_only(synth, tmp_path):
    f = _b(synth, 0)
    out = tmp_path / "creative_batch17" / "b"
    fb.write_frame(out, f)
    cen = fb.census(fb.load_frame(out))
    c17.assert_clean_result(cen)
    assert {"GBT", "GBA", "GBS", "GB1P", "GB2P"} <= set(cen["gates"]) and cen["gates"]["GBT"]["pass"] is True
    for g in ("GB1P", "GB2P"):
        assert set(cen["gates"][g]) <= {"se", "mde", "run", "label", "reason"}  # SE and MDE only, never a proxy estimate


# ---- the engine ------------------------------------------------------------------------------------------------------------------------------------------


def test_fixed_effect_engine_matches_cb16_and_separates_a_planted_effect_from_null():
    rng = np.random.default_rng(1)
    n, G = 600, 40
    g = rng.integers(0, G, n)
    x = rng.normal(size=n)
    eff = rng.normal(size=G)[g]
    y_null = eff + rng.normal(size=n)
    y_eff = eff + 1.5 * x + rng.normal(size=n)
    for y in (y_null, y_eff):
        v, b = win.fe_pseudo(y, x[:, None], g)
        v16, b16 = c16.fe_coef_pseudo(y, x[:, None], g, 0, None)
        assert b == pytest.approx(b16, abs=1e-9) and np.allclose(v, v16)
    ev = rng.integers(0, 25, n)
    D = win.set_ways({}, ev, ev % 5, 1_800_000_000.0 + rng.integers(0, 14, n) * DAY + rng.integers(0, 24, n) * H)
    idx = np.arange(n)
    eff_res = win.analyse(win.make_fe(y_eff, x, g), idx, D, 0.5)
    null_res = win.analyse(win.make_fe(y_null, x, g), idx, D, 0.5)
    assert eff_res["est"] == pytest.approx(1.5, abs=0.2) and eff_res["p"] < 0.01 and eff_res["floor_ok"]
    assert null_res["p"] > 0.01 and not null_res["floor_ok"]


def test_econ_test_needs_its_minimums_else_not_run_power_and_reports_a_difference():
    rng = np.random.default_rng(2)
    n = 900
    mk = rng.integers(0, 60, n)
    ev = mk // 2
    flag = rng.random(n) < 0.3
    rest = ~flag
    net = -2.0 * flag + rng.normal(0, 1.0, n) - 0.5
    D = win.set_ways({}, ev, mk % 7, 1_800_000_000.0 + rng.integers(0, 14, n) * DAY)
    r = win.econ_test(net, flag, rest, mk, D, min_fills=300, min_events=60, events=ev, rest_min=None)
    assert r["verdict"] == "not run (power)" and r["p"] == 1.0 and r["events"] == 30
    ev2 = mk
    r2 = win.econ_test(net, flag, rest, mk, D, min_fills=100, min_events=30, events=ev2, rest_min=100)
    assert r2["testable"] and r2["difference"]["est"] < -0.5 and r2["flagged_net"]["est"] < -1.0 and r2["decision"]["floors_ok"] and r2["p"] < 0.01
    assert r2["p"] == max(r2["difference"]["p"], r2["flagged_net"]["p"]) and r2["label"] == w.LABEL_ECON


def test_circular_shift_is_deterministic_and_keeps_each_units_multiset():
    vals = np.arange(12.0)
    unit = np.repeat([0, 1, 2], 4)
    t = np.arange(12.0)
    a = w.circular_shift(vals, unit, t, np.random.default_rng(7))
    b = w.circular_shift(vals, unit, t, np.random.default_rng(7))
    assert np.array_equal(a, b) and not np.array_equal(a, vals)
    for u in range(3):
        assert sorted(a[unit == u]) == sorted(vals[unit == u])


# ---- counting ---------------------------------------------------------------------------------------------------------------------------------------------


def test_count_lines_follow_branch_t_and_a_terminal_family_is_counted_exactly_once(tmp_path):
    trials = tmp_path / "t.jsonl"
    root = tmp_path / "creative_batch17"
    root.mkdir()
    win.log_family("B", {t: {"p": 0.5, "advance": False} for t in ("B1", "B2")}, trials_path=trials, results_sha256="x")
    win.log_family("C", {"C1": {"p": None, "testable": False, "advance": False}}, trials_path=trials, results_sha256="x")
    ls = [json.loads(x) for x in trials.read_text().splitlines()]
    assert {x["source"]: x["n_tests"] for x in ls if x["kind"] == "ml_explain"} == {"creative_batch_17:B": 2, "creative_batch_17:C": 1}
    assert all(x["n_tests"] == 0 for x in ls if x["kind"] == "cb17_test") and next(x for x in ls if x.get("hypothesis") == "C1")["p"] == 1.0
    with pytest.raises(Refused):
        win.log_family("A", {"A1": {"p": 0.5}}, trials_path=trials)
    with pytest.raises(Refused, match="every declared test"):
        win.log_family("B", {"B1": {"p": 0.5}}, trials_path=trials)
    with pytest.raises(Refused, match="not CB17-B"):
        win.log_family("B", {"B1-rep": {"p": 0.5}, "B1": {"p": 0.5}, "B2": {"p": 0.5}}, trials_path=trials)
    t1 = win.record_terminal(root, "B", w.NOT_TESTABLE_SOURCE, "smoke failed", trials_path=tmp_path / "t2.jsonl")
    t2 = win.record_terminal(root, "B", w.NOT_TESTABLE_SOURCE, "smoke failed", trials_path=tmp_path / "t2.jsonl")
    assert t1["newly_counted"] is True and t2["newly_counted"] is False
    assert sum(1 for x in (tmp_path / "t2.jsonl").read_text().splitlines() if '"ml_explain"' in x) == 1
    win.log_family("B", {"B1-rep": {"p": 0.2, "advance": True}}, replication=True, trials_path=trials, n_triggered=1)
    assert any(x["source"] == "creative_batch_17:B:rep" and x["n_tests"] == 1 for x in (json.loads(y) for y in trials.read_text().splitlines()) if x["kind"] == "ml_explain")


def test_smoke_failures_lists_unmet_criteria_and_requires_the_file(tmp_path):
    with pytest.raises(Refused, match="q0404 first"):
        win.smoke_failures(tmp_path / "smoke.json", "B")
    p = tmp_path / "smoke.json"
    crit = {k: True for k in w.SMOKE_CRITERIA}
    crit["reproduce_P2"] = False
    p.write_text(json.dumps({"criteria": crit}))
    assert win.smoke_failures(p, "B") == ["reproduce_P2"] and win.smoke_failures(p, "C") == [] and win.smoke_failures(p, "E") == []


def test_stage_one_decision_rules_use_k1_equals_three():
    h = w.stage1_holm({"B1": 0.004, "B2": None, "C1": 0.2})
    assert h["k1"] == 3 and h["tests"]["B1"]["reject"] is True and h["tests"]["B2"]["p"] == 1.0
    with pytest.raises(Refused):
        w.stage1_holm({"A1": 0.001})
    assert w.stage1_advance(0.009, True) and not w.stage1_advance(0.011, True) and not w.stage1_advance(0.001, False) and not w.stage1_advance(None, True)
    assert w.early_stage2_ok(0.006) and not w.early_stage2_ok(0.0063)
    assert math.isclose(w.STAGE_ALPHA / w.EARLY_ALPHA2_DIVISOR, 0.00625)
    with pytest.raises(Refused):
        w.stage2_final({"B1": 0.1})
    assert w.stage2_final({"B1-rep": 0.01, "C1-econ": None})["k2"] == 2
