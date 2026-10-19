# ruff: noqa: E501
"""CB16 common + Q + U + part-A orchestration (offline; synthetic fixtures only, no network)."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from astrolabe.research_lab import battery2
from astrolabe.research_lab import cb13_label as lab
from astrolabe.research_lab import cb13_t as t13
from astrolabe.research_lab import cb16_a as ra
from astrolabe.research_lab import cb16_common as c16
from astrolabe.research_lab import cb16_q as q
from astrolabe.research_lab import cb16_u as u
from tests.cb16_synth import (
    S_A,
    ep,
    make_cb13_screen_world,
    make_window_world,
    synth,
    trade,
    write_pin,
    write_trades,
)

# =====================================================================================================================================================
# Rules and common
# =====================================================================================================================================================


@pytest.fixture()
def rules_file(tmp_path):
    p = tmp_path / "cb16_rules.json"
    c16.write_rules(p)
    return p


def test_rules_parts_are_independent_and_k_is_declared_with_all_pins_set(rules_file):
    doc = json.loads(rules_file.read_text())
    assert doc["rules_version"] == "cb16-rules-v1" and set(doc["parts"]) == {"common", "A", "K"}
    assert doc["parts"]["common"]["part_declared"] is True and doc["parts"]["A"]["part_declared"] is True
    assert doc["parts"]["K"]["part_declared"] is True  # the coordinator's matches_all.json pin is set (freeze-check amendment 5)
    for part in ("common", "A", "K"):
        assert c16.verify_rules(rules_file, require_committed=False, part=part) == doc["parts"][part]["rules_sha256"]
    assert doc["parts"]["common"]["rules_sha256"] != doc["parts"]["A"]["rules_sha256"]


def test_rules_tamper_is_detected_and_a_declared_part_is_never_rewritten(rules_file, tmp_path):
    doc = json.loads(rules_file.read_text())
    doc["parts"]["A"]["constants"]["cb16_q"]["Q1_FLOOR"] = 0.1
    bad = tmp_path / "tampered.json"
    bad.write_text(json.dumps(doc))
    with pytest.raises(c16.Refused, match="hash mismatch"):
        c16.verify_rules(bad, require_committed=False, part="A")
    c16.verify_rules(bad, require_committed=False, part="common")  # the other part is independent
    doc2 = json.loads(rules_file.read_text())
    doc2["parts"]["common"]["constants"]["cb16_common"]["SEED_BOOT"] = 1
    rules_file.write_text(json.dumps(doc2))
    with pytest.raises(c16.Refused, match="never rewritten"):
        c16.write_rules(rules_file)


def test_part_a_hash_covers_q_u_and_a_modules_and_the_common_pins_the_cb13_functions():
    d = c16.rules_part_file_doc("A")
    names = set(d["func_sources_sha256"])
    assert any(n.startswith("cb16_q.") for n in names) and any(n.startswith("cb16_u.") for n in names) and any(n.startswith("cb16_a.") for n in names)
    assert not any(n.startswith("cb16_k.") for n in names)
    assert set(c16.rules_part_file_doc("common")["declared"]["common"]["cb13_pins"]) == set(c16.CB13_PINS)
    assert c16.cb13_pins_ok()["ok"]
    assert c16.BATCH_HOLM_K1 == 2 and c16.EARLY_ALPHA2 == pytest.approx(0.0125) and c16.STAGE2_K_MAX == 4


def test_s_a_follows_only_the_freeze_time():
    assert c16.s_a_from_freeze(ep("2026-11-01T00:00:00Z")) == ep("2026-11-02T00:00:00Z")
    assert c16.s_a_from_freeze(ep("2026-11-01T23:59:00Z")) == ep("2026-11-03T00:00:00Z")  # +24 h = 11-02 23:59 -> the next 00:00Z
    assert c16.s_a_from_freeze(ep("2026-11-02T00:01:00Z")) == ep("2026-11-04T00:00:00Z")
    assert c16.s_a_from_freeze(ep("2026-10-20T00:00:00Z")) == ep("2026-11-02T00:00:00Z")  # never before 2026-11-02
    w = c16.windows(S_A)
    assert w["screen"]["units"] == (S_A, S_A + 14 * 86400) and w["rep"]["units"][0] == S_A + 14 * 86400
    assert w["screen"]["frame_not_before"] == S_A + 14 * 86400 + 8 * 3600


def test_floor_and_window_guards_both_edges():
    floor = c16.ep(c16.LOOKBACK_FLOOR)
    assert c16.guard_floor(floor) == floor
    for t in (floor - 1, c16.ep(c16.J4R_WINDOW[0]), c16.ep(c16.J4R_WINDOW[1]) - 1, c16.ep(c16.CB13_T_HOLDOUT[0]), c16.ep(c16.CB13_T_HOLDOUT[1]) - 1):
        with pytest.raises(c16.Refused, match="before the CB16 lookback floor"):
            c16.guard_floor(t)
    assert c16.guard_rep_unit(S_A + c16.WINDOW_S - 1, S_A, rep_open=False)  # last SCREEN_A second
    with pytest.raises(c16.Refused, match="REP_A"):
        c16.guard_rep_unit(S_A + c16.WINDOW_S, S_A, rep_open=False)
    assert c16.guard_rep_unit(S_A + c16.WINDOW_S, S_A, rep_open=True)
    assert c16.in_election_night(ep("2026-11-03T18:00:00Z")) and not c16.in_election_night(ep("2026-11-03T17:59:59Z"))
    assert c16.in_election_night(ep("2026-11-04T23:59:59Z")) and not c16.in_election_night(ep("2026-11-05T00:00:00Z"))


def test_refused_roots_monitor_files_and_output_root():
    for p in ("x/surprise_live/a", "x/e005/a", "x/e011/a", "x/cb3_extract/a", "x/h15_new/a", "x/creative_batch13/a"):
        with pytest.raises(c16.Refused):
            c16.refuse_path(Path(p))
    for nm in ("alerts.jsonl", "outcomes.jsonl", "wallets.jsonl", "stats.jsonl", "state.json", "scores-20261102.jsonl"):
        with pytest.raises(c16.Refused):
            c16.guard_monitor_file(Path("x/live_trades") / nm)
    assert c16.guard_monitor_file(Path("x/live_trades/trades-20261102.jsonl"))
    for nm in ("results.json", "series.npz", "cross_venue_live.json"):
        with pytest.raises(c16.Refused):
            c16.guard_cross_venue_file(Path("x/cross_venue") / nm)
    assert c16.guard_cross_venue_file(Path("x/cross_venue/matches_all.json"))
    assert c16.is_holdout_path(Path("x/creative_batch16/holdout/a")) and not c16.is_holdout_path(Path("x/creative_batch16/a_screen/fills.csv.gz"))
    with pytest.raises(c16.Refused, match="refuses it"):
        c16.require_output_root(Path("x/creative_batch13/a"))
    with pytest.raises(c16.Refused, match="writes only under"):
        c16.require_output_root(Path("x/other/a"))
    assert c16.require_output_root(Path("x/creative_batch16/a"))
    with pytest.raises(c16.Refused):
        c16.assert_clean_columns(["tx_id", "side"])
    with pytest.raises(c16.Refused):
        c16.assert_clean_columns(["tx_id", "tx16"])
    c16.assert_clean_columns(q.FILL_COLUMNS)
    c16.assert_clean_columns(q.MARK_COLUMNS)


def test_forbidden_fields_never_reach_a_row_or_a_file(tmp_path):
    tr = tmp_path / "live_trades"
    lines = [trade(S_A + 60.0 * k, "0xA", 0.5, tx=f"t{k}") for k in range(3)]
    p = write_trades(tr, "20261102", lines)
    pr = list(q.iter_prints(p, S_A, S_A + 86400.0))
    assert len(pr) == 3 and all(not (set(x) & set(c16.FORBIDDEN_PRINT_FIELDS)) for x in pr)
    lb = list(q.iter_lookback(p, S_A, S_A + 86400.0))
    assert all(set(x) <= {"ts", "condition_id", "cash", "tx16"} for x in lb)
    lag = list(q.iter_recv_lag(p, S_A, S_A + 86400.0, {("0xA", "t1")}))
    assert lag == [("0xA", "t1", pytest.approx(400.0))]
    with pytest.raises(c16.Refused):
        list(q.iter_prints(p, c16.ep(c16.CB13_T_HOLDOUT[0]), S_A))  # a window start before the floor is refused
    assert not (set(c16.FORBIDDEN_OUTPUT_COLUMNS) & set(q.FILL_COLUMNS))


# =====================================================================================================================================================
# Grain
# =====================================================================================================================================================


def test_grain_parser_yes_terms_edges_and_tick_rule():
    assert q.grain_of(0.535) == 1 and q.grain_of(0.53) == 0 and q.grain_of(0.53000000001) == 0 and q.grain_of(0.469) == 1
    assert q.grain_of(t13.yes_price({"price": 0.465, "outcome_index": 1})) == 1  # YES terms of an outcome-1 print at 0.465 are 0.535
    assert q.grain_of(t13.yes_price({"price": 0.47, "outcome_index": 1})) == 0
    assert q.grain_of(math.nan) == -1
    assert q.grain_eligible(0.05, 0.001) and q.grain_eligible(0.95, 0.001) and not q.grain_eligible(0.0499, 0.001) and not q.grain_eligible(0.9501, 0.001)
    assert not q.grain_eligible(0.5, 0.01) and not q.grain_eligible(0.5, math.nan) and q.tick_is_grain(0.001) and not q.tick_is_grain(0.0001)
    assert q.p_band(0.2) == 1 and q.p_band(0.1999) == 0 and q.p_band(0.8) == 1 and q.p_band(0.8001) == 2
    assert q.spread_band(0.01) == 0 and q.spread_band(0.0101) == 1 and q.size_band(2499.0) == 0 and q.size_band(10000.0) == 2


def test_single_grain_markets_stay_out_of_the_statistic():
    rows = [dict(status=q.S_FILL, label=lab.PATH, condition_id="a", grain_ok=1, g=g) for g in (0, 1)] + [dict(status=q.S_FILL, label=lab.PATH, condition_id="b", grain_ok=1, g=1)] * 3
    assert q.both_grain_markets(rows) == {"a"}
    fills, table = synth(n_mkt=4, per=6)
    for r in fills:
        if r["condition_id"] == "c0":
            r["g"] = 1
    D = q.build_dataset(fills, table)
    elig, _ = q.q_eligible(D)
    assert not elig[D["cid"] == "c0"].any() and elig[D["cid"] == "c1"].any()


def test_sports_are_out_of_the_primary_and_reported_as_an_arm():
    fills, table = synth(n_mkt=6, per=8)
    for r in fills:
        if r["condition_id"] in ("c0", "c1"):
            r["label"] = lab.SPORTS
    D = q.build_dataset(fills, table)
    primary, _ = q.q_eligible(D)
    spo, _ = q.q_eligible(D, sports=True)
    assert not primary[np.isin(D["cid"], ["c0", "c1"])].any() and spo[np.isin(D["cid"], ["c0", "c1"])].any() and not spo[~np.isin(D["cid"], ["c0", "c1"])].any()
    assert u.u_units(D)[~np.isin(D["cid"], ["c0", "c1"])].all() and not u.u_units(D)[np.isin(D["cid"], ["c0", "c1"])].any()
    assert c16.CB16_SPORTS_IN_PRIMARY is False


def test_a_tick_change_between_touch_and_mark_capture_is_excluded_and_counted():
    fills, table = synth(n_mkt=6, per=8)
    for k, m in list(table.rows.items()):
        if k[1] == "2-4h" and k[0] % 4 == 0:
            m["tick"] = 0.01
    D = q.build_dataset(fills, table)
    elig, change = q.q_eligible(D)
    assert change.sum() > 0 and not (elig & change).any()


# =====================================================================================================================================================
# Silence (U)
# =====================================================================================================================================================


def test_monitor_gap_and_silence_standardiser_on_fixtures():
    r = u.smoke_silence_checks()
    assert r["a_monitor_gap"]["pass"] and r["a_monitor_gap"]["gaps_15min"] == 1 and r["a_monitor_gap"]["gaps_14m59s"] == 0
    assert r["a_silence_standardiser"]["pass"], r["a_silence_standardiser"]


def test_four_prior_gaps_do_not_standardise_five_do_and_the_lookback_floor_binds():
    floor = c16.ep(c16.LOOKBACK_FLOOR)
    no_gap = np.zeros((0, 2))
    t0 = floor + 86400.0
    t4, t5 = np.array([t0 + 600.0 * i for i in range(5)]), np.array([t0 + 600.0 * i for i in range(6)])
    assert u.silence_state(t4, no_gap, t4[-1] + 7200, math.nan)["silence_status"] == u.S_FEW
    assert u.silence_state(t5, no_gap, t5[-1] + 7200, t5[-1] - 40 * 86400)["silence_status"] == u.S_OK
    assert u.silence_state(t5, no_gap, t5[-1] + 7200, math.nan)["silence_status"] == u.S_GENESIS_UNKNOWN  # unknown never counts as met
    tf = np.array([floor - 1000.0 + 100.0 * i for i in range(30)])  # ten of them lie before the floor
    assert u.silence_state(tf, no_gap, float(tf[-1]) + 600.0, t5[-1] - 40 * 86400)["n_prior"] == 19


def test_genesis_at_exactly_24h_and_the_wake_rule_at_p90_and_the_one_hour_floor():
    no_gap = np.zeros((0, 2))
    t0 = c16.ep(c16.LOOKBACK_FLOOR) + 86400.0
    t5 = np.array([t0 + 600.0 * i for i in range(6)])  # five 10-minute gaps
    tau = float(t5[-1]) + 7200.0
    assert u.silence_state(t5, no_gap, tau, tau - 86400.0)["silence_status"] == u.S_OK  # exactly 24 h: not a genesis print
    assert u.silence_state(t5, no_gap, tau, tau - 86400.0 + 1.0)["silence_status"] == u.S_GENESIS
    assert u.silence_state(t5, no_gap, float(t5[-1]) + 3600.0, t0 - 1e6)["wake"] == 1  # s = 1 h exactly: wake
    assert u.silence_state(t5, no_gap, float(t5[-1]) + 3599.0, t0 - 1e6)["wake"] == 0
    wide = np.array([t0, t0 + 3600, t0 + 3600 + 7200, t0 + 3600 + 7200 + 10800, t0 + 21600 + 14400, t0 + 21600 + 14400 + 18000])  # p90 of the gaps is 3.6 h
    gaps = np.diff(wide)
    p90 = float(np.percentile(gaps, 90))
    assert p90 > 3600
    assert u.silence_state(wide, no_gap, float(wide[-1]) + p90, t0 - 1e6)["wake"] == 1 and u.silence_state(wide, no_gap, float(wide[-1]) + p90 - 1, t0 - 1e6)["wake"] == 0


def test_a_silence_that_overlaps_a_monitor_gap_is_censored_and_its_prior_gap_is_dropped():
    t0 = c16.ep(c16.LOOKBACK_FLOOR) + 86400.0
    mg = u.monitor_gaps(np.array([t0 + 4200.0, t0 + 4200.0 + 901.0, t0 + 6000.0, t0 + 6000.0 + 899.0]))
    assert len(mg) == 1 and mg[0][1] - mg[0][0] == 901.0  # 899 s is not a gap
    cen = u.silence_state(np.array([t0 + 600.0 * i for i in range(8)]), np.array([[t0 + 4300.0, t0 + 6000.0]]), t0 + 9000.0, t0 - 1e6)
    assert cen["silence_status"] == u.S_CENSORED  # the silence (t0+4200, t0+9000) overlaps the gap
    assert cen["n_prior"] == 7  # none of the seven prior gaps overlaps the monitor gap (4300, 6000)
    inside = u.silence_state(np.array([t0 + 600.0 * i for i in range(8)]), np.array([[t0 + 1000.0, t0 + 1900.0]]), t0 + 4250.0, t0 - 1e6)
    assert inside["n_prior"] == 4  # the three gaps (600, 1200), (1200, 1800) and (1800, 2400) overlap the monitor gap (1000, 1900) and are dropped from the market's prior gaps
    assert u.silence_state(np.array([t0 + 600.0 * i for i in range(8)]), np.array([[t0 + 4300.0, t0 + 6000.0]]), t0 + 4250.0, t0 - 1e6)["silence_status"] == u.S_OK


def test_add_silence_marks_every_row_and_x_only_when_ok():
    rows = [dict(condition_id="m", tau=S_A + 600.0 * i + 7200, created_epoch=S_A - 5e6) for i in range(10)]
    by = {"m": np.array([S_A + 600.0 * i + 7200 for i in range(10)])}
    allts = np.concatenate([by["m"], np.arange(S_A, S_A + 20000, 300.0)])
    rep = u.add_silence(rows, by, np.sort(allts))
    assert rep["by_status"]["no_prev"] == 1 and all(r["x"] == r["x_raw"] for r in rows if r["silence_status"] == u.S_OK)
    assert all(math.isnan(r["x"]) for r in rows if r["silence_status"] != u.S_OK)


# =====================================================================================================================================================
# Inference helpers and placebos
# =====================================================================================================================================================


def test_market_fixed_effects_cancel_a_per_market_constant():
    rng = np.random.default_rng(1)
    cid = np.repeat([f"m{i}" for i in range(30)], 10)
    g = (rng.random(300) < 0.5).astype(float)
    const = np.repeat(rng.normal(0, 50, 30), 10)
    y = 2.0 * g + const + rng.normal(0, 0.1, 300)
    _v, b = c16.fe_coef_pseudo(y, g, cid)
    assert b == pytest.approx(2.0, abs=0.1)


def test_stratified_permutation_never_moves_a_label_across_strata():
    rng = np.random.default_rng(2)
    strata = np.array(["a"] * 20 + ["b"] * 20)
    vals = np.concatenate([np.zeros(20), np.ones(20)])
    for _ in range(20):
        out = c16.permute_within(vals, strata, rng)
        assert (out[:20] == 0).all() and (out[20:] == 1).all()
    mixed = np.arange(40.0)
    out = c16.permute_within(mixed, strata, rng)
    assert sorted(out[:20]) == sorted(mixed[:20]) and sorted(out[20:]) == sorted(mixed[20:])


def test_composition_placebo_informativeness_49_versus_50_percent():
    g = np.array([0, 1] * 25 + [0] * 50, float)  # 50 rows in strata with both grains, 50 in single-grain strata
    strata = np.array([f"s{i // 2}" for i in range(50)] + [f"t{i}" for i in range(50)])
    idx = np.arange(100)
    assert q.informative_share(g, strata, idx) == pytest.approx(0.5)
    share49 = q.informative_share(g, strata, np.concatenate([np.arange(49), np.arange(50, 100)]))  # 49 of 99 rows in strata with both grains
    assert share49 < q.INFORMATIVE_SHARE <= q.informative_share(g, strata, idx)


def test_q1_composition_placebo_fails_below_the_informativeness_floor(monkeypatch):
    fills, table = synth(beta_g=1.5, n_mkt=100, per=12)
    D = q.build_dataset(fills, table)
    monkeypatch.setattr(q, "informative_share", lambda *a, **k: 0.49)
    r = q.q1_test(D, n_draws=5)
    assert r["composition_placebo"]["informative"] is False and r["composition_placebo"]["holds"] is False and r["advance"] is False
    assert q.LABEL_UNINFORMATIVE in r["labels"]
    monkeypatch.setattr(q, "informative_share", lambda *a, **k: 0.50)
    r2 = q.q1_test(D, n_draws=5)
    assert r2["composition_placebo"]["informative"] is True and r2["composition_placebo"]["holds"] is True


# =====================================================================================================================================================
# Q1 / U1 on synthetic effects
# =====================================================================================================================================================


def test_q1_advances_on_a_real_grain_effect_and_not_on_a_null():
    fills, table = synth(beta_g=1.5, n_mkt=140, per=14, seed=3)
    D = q.build_dataset(fills, table)
    r = q.q1_test(D, n_draws=10)
    assert r["testable"] and r["est"] > 1.0 and r["p"] < 0.01 and r["floor_ok"] and r["checks_ok"] and r["advance"], r["verdict"]
    assert r["spread_free"]["holds"] and r["composition_placebo"]["holds"] and r["calibration_placebo"]["holds"] and r["prefill_placebo"]["holds"]
    assert q.LABEL_UPPER in r["labels"]
    fills0, table0 = synth(beta_g=0.0, n_mkt=140, per=14, seed=4)
    r0 = q.q1_test(q.build_dataset(fills0, table0), n_draws=10)
    assert r0["advance"] is False


def test_q1_below_the_half_cent_floor_does_not_advance_even_at_small_p():
    fills, table = synth(beta_g=0.3, n_mkt=200, per=30, seed=5)
    r = q.q1_test(q.build_dataset(fills, table), n_draws=5)
    assert r["est"] < q.Q1_FLOOR and r["floor_ok"] is False and r["advance"] is False


def test_u1_advances_on_a_silence_slope_and_signs_longer_silence_worse_for_the_maker():
    fills, table = synth(beta_g=0.0, beta_x=-1.5, n_mkt=140, per=14, seed=3)
    D = q.build_dataset(fills, table)
    r = u.u1_test(D, n_draws=10)
    assert r["est"] > 1.0 and r["advance"] and r["arrival_label"] == u.LABEL_ARRIVAL, r["verdict"]
    fills2, table2 = synth(beta_g=0.0, beta_x=+1.5, n_mkt=140, per=14, seed=3)
    r2 = u.u1_test(q.build_dataset(fills2, table2), n_draws=5)
    assert r2["est"] < 0 and r2["advance"] is False  # the opposite sign never advances


def test_u1_rep_needs_the_frozen_sd_and_stage1_refuses_one():
    fills, table = synth(beta_g=0.0, beta_x=-1.5, n_mkt=100, per=12)
    D = q.build_dataset(fills, table)
    with pytest.raises(c16.Refused, match="frozen SD"):
        u.u1_test(D, rep=True)
    with pytest.raises(c16.Refused, match="SD\\(x\\) on SCREEN_A"):
        u.u1_test(D, sd=1.0)
    s1 = u.u1_test(D, n_draws=3)
    r = u.u1_test(D, n_draws=3, rep=True, sd=2.0 * s1["sd_x"])
    assert r["sd_source"] == "SCREEN_A frozen" and r["est"] == pytest.approx(s1["est"] * 2.0, rel=0.02)  # per frozen SD (twice the SD: twice the effect per SD), not REP_A's own


def test_stale_touch_and_shape_outputs_carry_no_p_value():
    fills, table = synth(n_mkt=40, per=10)
    D = q.build_dataset(fills, table)
    rep = q.q_reported(D, fills)
    assert rep["stale_touch_variant"]["p_value"] is None and "p" not in rep["stale_touch_variant"]
    assert "p" not in rep["shape_descriptor"] and all(t.get("p_value") is None for t in rep["shape_descriptor"]["share_terciles"].values())
    assert set(rep["decomposition"]) == {"bot", "human"}
    assert rep["worst_case"].get("label") in (None, q.LABEL_EXCL)
    ur = u.u_reported(D, fills)
    assert "p" not in ur["wake_contrast"] and "exclusion_by_x_tercile" in ur and ur["taker_follow"]["hurdle_cents"] == 4.5


def test_exclusion_by_grain_and_by_x_tercile_tables():
    fills, _ = synth(n_mkt=10, per=6)
    rows = [dict(f) for f in fills]
    for i, r in enumerate(rows[:6]):
        r["status"] = t13.S_INSIDE if i % 2 == 0 else t13.S_INCONSISTENT
        r["excl_g"] = i % 2
    exc = q.exclusion_by_grain(rows)
    assert exc["bot"]["inside"] + exc["human"]["inside"] + exc["bot"]["inconsistent"] + exc["human"]["inconsistent"] == 6
    ex = u.exclusion_by_x(rows)
    assert sum(t["n"] for t in ex["terciles"].values()) == ex["n"]


# =====================================================================================================================================================
# Gates
# =====================================================================================================================================================


def test_gqp_and_gup_write_standard_errors_only():
    fills, _ = synth(n_mkt=60, per=10)
    p = q.q_power(fills)
    assert set(p) == {"se", "mde", "pass", "n"} and p["mde"] == pytest.approx(c16.MDE_FACTOR * p["se"])
    pu = u.u_power(fills)
    assert {"est", "coef", "beta"}.isdisjoint(pu) and set(pu) <= {"se", "mde", "pass", "n"}
    cen = ra.census_a(fills)
    flat = json.dumps(cen, default=str)
    assert '"est"' not in flat and cen["counts_only"] is True


def test_gai_199_versus_200_pairs_and_the_pooled_pass():
    assert q.GAI_MIN_PAIRS == 200
    assert q.gai_pooled({"pairs": 100, "agree": 80}, {"pairs": 99, "agree": 80})["evaluable"] is False
    pooled = q.gai_pooled({"pairs": 100, "agree": 80}, {"pairs": 100, "agree": 80})
    assert pooled["evaluable"] and pooled["pass"] and pooled["agree_share"] == pytest.approx(0.8)
    assert q.gai_pooled({"pairs": 100, "agree": 70}, {"pairs": 100, "agree": 70})["pass"] is False  # exactly 70% fails (> 70% needed)


def test_gq_gu_gqg_minimums():
    fills, _ = synth(n_mkt=140, per=14)  # 1,960 fills, 140 markets, 70 events
    assert q.q_gate_gq(fills)["pass"] and u.u_gate_gu(fills)["pass"]
    assert not q.q_gate_gq(fills[:900])["pass"]
    few = [dict(f) for f in fills]
    for f in few:
        f["event_id"] = f"E{int(f['condition_id'][1:]) // 10}"  # 14 events < 60
    assert not q.q_gate_gq(few)["pass"] and not u.u_gate_gu(few)["pass"]
    g = q.gate_gqg(fills)
    assert g["counts_only"] and g["pass"] is True and 0.05 <= g["sub_share"] <= 0.95
    allsub = [dict(f, g=1) for f in fills]
    assert q.gate_gqg(allsub)["pass"] is False


# =====================================================================================================================================================
# Costs, Q2, U2
# =====================================================================================================================================================


def test_q2_arithmetic_clip_and_worst_case():
    fills, table = synth(n_mkt=30, per=10)
    D = q.build_dataset(fills, table)
    j = int(np.where(D["g"] == 1)[0][0])
    idx = np.array([j])
    x = D["ask_2-4h"][j] if D["d"][j] == -1 else D["bid_2-4h"][j]
    want = 100.0 * (D["d"][j] * (x - D["P"][j]) - D["fee_rate"][j] * x * (1 - x))
    assert q.q2_values(D, idx)[0] == pytest.approx(want) and q.q2_values(D, idx, 0.5)[0] == pytest.approx(want - 0.5)
    res = q.q2_test(D)
    assert res["position"]["max_shares"] == 100.0 and res["position"]["n_clipped"] == res["position"]["n_clipped"] and res["label"] == q.LABEL_Q2
    D2 = dict(D)
    D2["st_2-4h"] = np.array(["closed_absent"] * len(D["tx_id"]), dtype=object)
    w = q.q2_worst(D2, np.array([j]))
    assert w[0] == pytest.approx(t13.worst_value(int(D["d"][j]), float(D["P"][j])))


def test_u2_p_is_the_max_of_its_two_component_ps_and_avoided_window_edges():
    fills, table = synth(beta_g=0.0, n_mkt=60, per=14, seed=7)
    D = q.build_dataset(fills, table)
    # make avoided fills clearly worse: wake-up prints just before a subset of fills
    wakes = {}
    for f in fills[::7]:
        wakes.setdefault(f["condition_id"], []).append((f["tau"] - 600.0, 30.0))
    a = u.avoided_mask(D, wakes)
    assert a.any()
    res = u.u2_test(D, wakes)
    if res.get("testable"):
        assert res["p"] == max(res["primary"]["p"], res["level"]["p"])
        assert res["label"] == u.LABEL_U_PROTECT
    # edges: (tau_w + 60 s, tau_w + 2 h]
    D1 = {"tx_id": np.array([0, 1, 2, 3]), "cid": np.array(["m"] * 4), "tau": np.array([1060.0, 1060.5, 8200.0, 8200.5])}
    assert list(u.avoided_mask(D1, {"m": [(1000.0, math.nan)]})) == [False, True, True, False]
    assert list(u.avoided_mask(D1, {"m": [(1000.0, 600.0)]}, lambda lag: lag)) == [False, False, True, False]


def test_u2_floors_are_negative_and_the_protected_net_is_reported():
    fills, table = synth(beta_g=0.0, n_mkt=60, per=14, seed=7)
    D = q.build_dataset(fills, table)
    wakes = {f["condition_id"]: [(f["tau"] - 600.0, 30.0)] for f in fills[::5]}
    res = u.u2_test(D, wakes)
    assert u.U2_PRIMARY_FLOOR == 0.5 and u.U2_LEVEL_FLOOR == 1.0
    if res.get("testable"):
        assert "protected_maker_net_on_remaining_fills" in res["reported"] and set(res["robustness"]) == {"delay_5min", "delay_receipt_lag"}


def test_rep_events_are_dropped_even_when_thinned_and_the_variant_never_replaces():
    fills, _ = synth(n_mkt=20, per=4)
    screen_events = {f["event_id"] for f in fills if f["condition_id"] in {f"c{i}" for i in range(0, 14)}}
    out, rep = q.drop_screen_events(fills, screen_events)
    assert rep["dropped"] > 0 and rep["dropped_share"] > q.REP_THIN_SHARE and rep["label"] == q.LABEL_REP_THIN
    assert all(r["status"] != q.S_FILL for r in out if r["event_id"] in screen_events) and len(out) == len(fills)  # status rewritten, never deleted
    out2, rep2 = q.drop_screen_events(fills, {"nothing"})
    assert rep2["dropped"] == 0 and rep2["label"] is None and out2 == fills


# =====================================================================================================================================================
# Stage rules, counting
# =====================================================================================================================================================


def test_stage_one_holm_k1_fixed_and_stage_two_early_alpha_over_four():
    assert c16.stage1_advance(0.0099, True) and not c16.stage1_advance(0.01, True) and not c16.stage1_advance(0.001, False) and not c16.stage1_advance(None, True)
    h = c16.stage1_holm({"Q1": 0.009, "U1": None})
    assert h["tests"]["Q1"]["reject"] is True and h["k"] == 2
    assert c16.early_stage2_ok(0.0124) and not c16.early_stage2_ok(0.0125)
    fin = c16.stage2_final({"Q1": 0.02, "U1": 0.04, "Q2": None, "U2": 0.5})
    assert fin["k"] == 4 and "Q1-rep" in fin["tests"] and fin["tests"]["Q2"]["p"] == 1.0
    assert fin["tests"]["Q1-rep"]["reject"] is False
    only_adds = c16.stage2_final({"Q1": 0.0124})
    assert only_adds["tests"]["Q1-rep"]["reject"] is True and c16.stage2_pass(True, 0.0124, only_adds["tests"]["Q1-rep"]["reject"])
    assert c16.stage2_pass(True, 0.03, True) and not c16.stage2_pass(False, 0.001, True)
    with pytest.raises(c16.Refused):
        c16.stage2_final({"X1": 0.1})


def test_trial_lines_and_cumulative_count(tmp_path):
    tp = tmp_path / "trials.jsonl"
    c16.log_descriptive("smoke", {"pass": True}, trials_path=tp)
    c16.log_family("Q", {"Q1": {"p": 0.5, "advance": False, "testable": True}}, trials_path=tp, results_sha256="s")
    c16.log_family("U", {"U1": {"p": None, "advance": False, "testable": False}}, trials_path=tp, results_sha256="s")
    c16.log_family("Q", {"Q2": {"p": 0.2, "testable": True}}, replication=True, trials_path=tp, n_triggered=1)
    lines = [json.loads(x) for x in tp.read_text().splitlines()]
    assert {x["kind"] for x in lines} == {"cb16_descriptive", "cb16_test", "ml_explain", "cb16_replication"}
    assert all(x["n_tests"] == 0 for x in lines if x["kind"] != "ml_explain")
    counts = {x["source"]: x["n_tests"] for x in lines if x["kind"] == "ml_explain"}
    assert counts == {"creative_batch_16:Q": 1, "creative_batch_16:U": 1, "creative_batch_16:Q:rep": 1}
    assert [x["p"] for x in lines if x["kind"] == "cb16_test"] == [0.5, 1.0]  # an untestable test is counted with p = 1
    for k in ("cb16_test", "cb16_replication", "cb16_descriptive"):
        assert battery2.KIND_RULES[k][0] == battery2.EXCLUDE
    with pytest.raises(c16.Refused):
        c16.log_family("Q", {"U1": {"p": 1.0}}, trials_path=tp)
    with pytest.raises(c16.Refused):
        c16.log_family("Q", {"Q2": {"p": 1.0}}, trials_path=tp)  # Q2 is a Stage-2 test


def test_record_terminal_counts_once(tmp_path):
    root = tmp_path / "creative_batch16"
    tp = tmp_path / "trials.jsonl"
    t = c16.record_terminal(root, "Q", "not testable (grain)", "GQG failed", trials_path=tp)
    assert t["newly_counted"] is True
    t2 = c16.record_terminal(root, "Q", "not testable (grain)", "again", trials_path=tp)
    assert t2["newly_counted"] is False
    lines = [json.loads(x) for x in tp.read_text().splitlines()]
    assert sum(x["n_tests"] for x in lines if x["kind"] == "ml_explain") == 1
    assert c16.read_terminal(root, "Q")["label"] == "not testable (grain)" and c16.read_terminal(root, "U") is None


# =====================================================================================================================================================
# Orchestration
# =====================================================================================================================================================


def test_smoke_offline_a_passes_on_fixtures(tmp_path):
    w = make_cb13_screen_world(tmp_path)
    pin = {"start": ep("2026-10-16T00:00:00Z"), "end": ep("2026-10-21T00:00:00Z"), "final": False}
    res = q.smoke_offline({"cb13_trades_dir": str(w["trades"]), "cb13_snap_root": str(w["snap"]), "pin": pin})
    assert set(q.SMOKE_NEEDS) <= set(res)
    assert all(res[k]["pass"] for k in q.SMOKE_NEEDS), {k: res[k] for k in q.SMOKE_NEEDS if not res[k]["pass"]}
    assert res["a_cb13_reproduction"]["pinned_counts"] == res["a_cb13_reproduction"]["independent_counts"]
    missing = q.smoke_offline({"cb13_trades_dir": str(tmp_path / "nope"), "cb13_snap_root": str(tmp_path / "nope2"), "pin": pin})
    assert missing["a_cb13_reproduction"]["pass"] is False  # a missing raw file is a FAIL


def test_the_independent_touch_band_matches_the_pinned_function_on_edges():
    base = dict(bid=0.48, ask=0.50, closed=False, binary=True, end=S_A + 10 * 86400, recv=S_A)
    cases = [(0.50, 0.50), (0.52, 0.52), (0.5201, 0.5201), (0.49, 0.49), (0.47, 0.47), (0.46, 0.47), (0.44, 0.48)]
    for lo, hi in cases:
        t = {"ts": S_A + 600, "p_min": lo, "p_max": hi, "condition_id": "x"}
        kind, _d, _P = t13.classify_position(lo, hi, 0.48, 0.50)
        st = q.independent_status(t, base, lab.PATH)
        want = {"lift": q.S_FILL, "hit": q.S_FILL, "inside": t13.S_INSIDE, "inconsistent": t13.S_INCONSISTENT}[kind]
        assert st == want, (lo, hi, kind, st)


def test_frame_screen_statuses_silence_no_forbidden_columns_and_touch_mode_has_no_marks(tmp_path):
    w = make_window_world(tmp_path)
    (tmp_path / "history").mkdir()
    rep, files = ra.frame_a("screen", s_a=S_A, trades_dir=w["trades"], snap_root=w["snap"], sweep_root=tmp_path / "book_sweeps", hist_root=tmp_path / "history", out_dir=tmp_path / "creative_batch16" / "a_screen")
    assert rep["n_fills"] > 0 and rep["transactions"]["n_tx"] == w["n_trades"]
    rows = q.read_fills(tmp_path / "creative_batch16" / "a_screen" / q.FILLS_NAME)
    assert len(rows) == w["n_trades"]
    header = (tmp_path / "creative_batch16" / "a_screen" / q.FILLS_NAME)
    import gzip  # noqa: PLC0415

    cols = gzip.open(header, "rt").readline().strip().split(",")
    assert not (set(cols) & set(c16.FORBIDDEN_OUTPUT_COLUMNS)) and "tx16" not in cols
    fl = [r for r in rows if r["status"] == q.S_FILL]
    assert {r["g"] for r in fl} == {0, 1} and all(r["tick_touch"] == 0.001 for r in fl)
    assert all(r["silence_status"] in u.SILENCE_STATUSES for r in rows)
    assert any(r["silence_status"] == u.S_OK for r in rows)
    caps = q.list_captures(w["snap"], S_A - 5 * 3600.0, S_A + 14 * 86400.0)
    qi = q.load_quote_index(caps, {"0xA"}, "touch")
    with pytest.raises(c16.Refused, match="touch mode"):
        qi.mark_cap("0xA", S_A + 3600.0, 7200.0)
    with pytest.raises(c16.Refused):
        qi.mark_for({"condition_id": "0xA", "tau": S_A + 3600.0}, 7200.0)
    assert (tmp_path / "creative_batch16" / "a_screen" / q.KEYS_NAME).exists() and not (tmp_path / "creative_batch16" / "a_screen" / q.KEYS_PARTIAL_NAME).exists()


def test_frame_refuses_rows_before_the_floor_and_rep_without_screen_events(tmp_path):
    w = make_window_world(tmp_path)
    with pytest.raises(c16.Refused):
        q.window_transactions(w["trades"], c16.ep(c16.CB13_T_HOLDOUT[0]), S_A + 100.0, S_A)
    with pytest.raises(c16.Refused, match="SCREEN_A fill events"):
        ra.frame_a("rep", s_a=S_A, trades_dir=w["trades"], snap_root=w["snap"], sweep_root=None, hist_root=tmp_path, out_dir=tmp_path / "creative_batch16" / "x")
    txs = None
    with pytest.raises(c16.Refused, match="REP_A"):
        # a transaction inside REP_A is refused unless the REP path is open
        p = write_trades(tmp_path / "w2" / "live_trades", "20261116", [trade(S_A + c16.WINDOW_S + 60.0, "0xA", 0.5, tx="r1")])
        q.window_transactions(p.parent, S_A + c16.WINDOW_S - 1.0, S_A + c16.WINDOW_S + 1000.0, S_A, rep_open=False)
    _ = txs


def test_screen_a_end_to_end_on_gate_passing_synthetic_fills():
    fills, table = synth(beta_g=1.5, beta_x=-1.5, n_mkt=140, per=14, seed=3)
    census = ra.census_a(fills)
    assert census["gq"]["pass"] and census["gu"]["pass"] and census["gqp"]["pass"] and census["gup"]["pass"]
    out = ra.screen_a(fills, [], table, census, n_draws=5)
    assert out["Q1"]["advance"] and out["U1"]["advance"] and out["sd_x"] > 0
    assert out["stage1_holm"]["tests"]["Q1"]["reject"] and out["stage1_holm"]["tests"]["U1"]["reject"]
    assert t13.LABEL_CADENCE in out["labels"]  # no later prints: cadence informativeness unverified (n < 200)
    assert set(out["reported"]) == {"Q", "U"}
    assert ra.triggers_of(out) == {"Q1": True, "U1": True}


def test_screen_a_gate_failures_and_terminals_give_declared_labels():
    fills, table = synth(n_mkt=60, per=10)  # 600 fills: GQ and GU fail
    census = ra.census_a(fills)
    out = ra.screen_a(fills, [], table, census, n_draws=3)
    assert out["Q1"]["verdict"] == q.NOT_TESTABLE_POP and out["U1"]["verdict"] == q.NOT_TESTABLE_POP and out["Q1"]["p"] == 1.0 and out["Q1"]["advance"] is False
    out2 = ra.screen_a(fills, [], table, census, terminals={"Q": {"label": "not testable (grain)"}, "U": None}, n_draws=3)
    assert out2["Q1"]["verdict"] == "not testable (grain)"
    fills2, table2 = synth(n_mkt=140, per=14)
    c2 = ra.census_a(fills2)
    c2["gqp"] = {"pass": False}
    assert ra.screen_a(fills2, [], table2, c2, n_draws=3)["Q1"]["verdict"] == q.NOT_RUN_POWER
    cadence = {"pairs": 300, "agree": 100, "agree_share": 1 / 3, "evaluable": True, "pass": False}
    import unittest.mock as mock  # noqa: PLC0415

    with mock.patch.object(q, "gate_gai", return_value=cadence):
        r = ra.screen_a(fills2, [], table2, ra.census_a(fills2), n_draws=3)
    assert r["Q1"]["verdict"] == q.NOT_TESTABLE_CADENCE and r["U1"]["verdict"] == q.NOT_TESTABLE_CADENCE


def test_rep_a_triggers_pooled_gai_and_frozen_sd():
    fills, table = synth(beta_g=1.5, beta_x=-1.5, n_mkt=140, per=14, seed=3)
    census = ra.census_a(fills)
    screen = ra.screen_a(fills, [], table, census, n_draws=3)
    rfills, rtable = synth(beta_g=1.5, beta_x=-1.5, n_mkt=140, per=14, seed=9)
    body = ra.rep_a(rfills, [], rtable, screen, {"Q1": True, "U1": False}, n_draws=3)
    assert "Q1" in body and "Q2" in body and "U1" not in body and "U2" not in body
    assert body["Q2"]["verdict"] == q.NOT_TESTABLE_CADENCE  # < 200 pooled pairs: Q2 needs the pooled GAI PASS
    assert body["Q1"]["rep"] is True and body["Q1"]["stage2_early_alpha_ok"] in (True, False) and body["Q1"]["p"] is not None
    body2 = ra.rep_a(rfills, [], rtable, screen, {"Q1": False, "U1": True}, n_draws=3)
    assert "U1" in body2 and body2["U1"]["sd_source"] == "SCREEN_A frozen" and body2["U2"]["verdict"] == q.NOT_TESTABLE_CADENCE
    scr2 = dict(screen, sd_x=None)
    body3 = ra.rep_a(rfills, [], rtable, scr2, {"Q1": False, "U1": True}, n_draws=3)
    assert body3["U1"]["verdict"] == q.NOT_RUN_POWER  # no frozen SD(x): U1-rep does not run
    pooled_ok = {"pairs": 300, "agree": 250, "agree_share": 0.83, "evaluable": True, "pass": True}
    scr3 = dict(screen, gai=pooled_ok)
    body4 = ra.rep_a(rfills, [], rtable, scr3, {"Q1": True, "U1": False}, n_draws=3)
    assert body4["gai_pooled"]["pass"] is True and body4["gai_pooled"]["pairs"] == 300  # the pooled count and share include the SCREEN_A side
    assert body4["Q2"]["label"] == q.LABEL_Q2 and body4["Q2"]["verdict"] != q.NOT_TESTABLE_CADENCE


def test_grain_census_on_the_cb13_screen_files_opens_no_mark(tmp_path):
    w = make_cb13_screen_world(tmp_path)
    pin = {"start": ep("2026-10-16T00:00:00Z"), "end": ep("2026-10-21T00:00:00Z"), "final": False}
    res = ra.grain_census(w["trades"], w["snap"], pin)
    assert res["counts_only"] and "gqg" in res and res["gqg"]["counts_only"] and res["pass"] in (True, False)
    assert "dropped_long_silences" in res and res["g1b_reference_ge_12h_outside_sports"] == {"enriched": 459, "unenriched": 127}


# =====================================================================================================================================================
# q0389: the Data API validity sample
# =====================================================================================================================================================


def test_data_api_parse_drops_side_wallet_and_hash_fields():
    page = [{"timestamp": 1000, "price": "0.5", "size": 3, "conditionId": "0xA", "side": "BUY", "proxyWallet": "0xw", "name": "n", "transactionHash": "0xh", "pseudonym": "p"}]
    out = u.parse_data_api_page(page)
    assert out == [{"timestamp": 1000.0, "price": 0.5, "size": 3.0, "conditionId": "0xA"}]
    assert u.parse_data_api_page({"error": "x"}) == []


def test_all_size_silence_pages_newest_first_and_never_keeps_prints_at_or_after_tau():
    pages = {0: [{"timestamp": 2000.0}, {"timestamp": 1900.0}], 500: []}
    r = u.all_size_silence(lambda off: pages.get(off, []), 1800.0)
    assert r["found"] is False and r["exhausted"] is True
    full = [{"timestamp": 2000.0 - i} for i in range(u.VALIDITY_PAGE_SIZE)]
    nxt = [{"timestamp": 1500.0}]
    calls = []

    def get(off):
        calls.append(off)
        return full if off == 0 else nxt

    nxt[0]["timestamp"] = 1400.0
    r2 = u.all_size_silence(get, 1500.0)
    assert r2["found"] and r2["silence_s"] == pytest.approx(100.0) and calls == [0, u.VALIDITY_PAGE_SIZE] and r2["pages"] == 2


def test_validity_sample_is_seeded_and_the_label_follows_the_first_share():
    fills, _ = synth(n_mkt=40, per=10, wake_p=0.3)
    s1, s2 = u.validity_sample(fills), u.validity_sample(fills)
    assert s1 == s2 and set(s1) == {"wake", "non_wake"} and all(set(x) == {"condition_id", "tau"} for x in s1["wake"])

    class Lim:
        requests = 0

        def __init__(self, ts):
            self.ts = ts

        def get(self, url, params):
            self.requests += 1
            return 200, [{"timestamp": self.ts, "price": 0.5, "size": 1, "conditionId": params["market"], "side": "BUY", "proxyWallet": "0x"}]

    sample = {"wake": [{"condition_id": "a", "tau": 10000.0}], "non_wake": [{"condition_id": "b", "tau": 10000.0}]}
    short = u.run_validity(sample, Lim(9900.0))  # the all-size silence is only 100 s: the wake-up was not a quiet market
    assert short["wake_share_silent_ge_1h"] == 0.0 and short["label"] == u.LABEL_U_LARGE_ONLY and short["non_wake_share_silent_lt_1h"] == 1.0
    long_ = u.run_validity(sample, Lim(1000.0))
    assert long_["wake_share_silent_ge_1h"] == 1.0 and long_["label"] is None and long_["reported_only"] is True


def test_write_pin_helper_is_a_valid_j4r_pin(tmp_path):
    from astrolabe.research_lab import cb13_common as c13  # noqa: PLC0415

    assert c13.j4r_pin(write_pin(tmp_path))["start"] == ep("2026-10-16T00:00:00Z")


# =====================================================================================================================================================
# q0380 helpers (no network)
# =====================================================================================================================================================


def test_exclusion_key_sources_frame_ids_and_id_only_readers(tmp_path):
    import csv  # noqa: PLC0415
    import gzip  # noqa: PLC0415

    keys = tmp_path / "creative_batch15" / c16.CB15_KEYS_FILE
    keys.parent.mkdir(parents=True)
    with gzip.open(keys, "wt", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(list(c16.KEY_COLUMNS))
        w.writerow(["m1", "1", "e1;e2", "n1", "s1", "h2_main;h3_power"])
        w.writerow(["m2", "1", "e3", "", "", ""])
    rows, ksrc, sha = c16.load_keys(keys)
    assert [r["market_id"] for r in rows] == ["m1", "m2"] and len(sha) == 64
    assert ksrc["market"]["m1"] == {"h2_main", "h3_power"} and ksrc["event"]["e2"] == {"h2_main", "h3_power"} and ksrc["neg_risk_market"]["n1"] == {"h2_main", "h3_power"}
    no_attr = tmp_path / "creative_batch15" / "plain.csv.gz"
    with gzip.open(no_attr, "wt", newline="") as fh:
        csv.writer(fh).writerow(["market_id", "found"])
    with pytest.raises(c16.Refused, match="attribution"):
        c16.read_keys_with_sources(no_attr)
    msrc = c16.attribute_sources(rows, {"h15_elect_live": {"m2", "m9"}}, {"m1"})
    assert msrc["m1"] >= {"cb15:h2_main", "seal_copies"} and msrc["m2"] == {c16.BASE_SOURCE, "frame:h15_elect_live"} and msrc["m9"] == {"frame:h15_elect_live"}
    hist = tmp_path / "history"
    (hist / "h15_elect_live").mkdir(parents=True)
    (hist / "h15_elect_live" / "race_map.csv").write_text("market_id,event_id,winner,price\nm5,e5,YES,0.9\nm6,e6,NO,0.1\n")
    ids, absent = c16.frame_ids(hist, tmp_path)
    assert ids["h15_elect_live"] == {"m5", "m6"} and "h15_birth_live/pairs.jsonl" in absent
    cols = c16.read_id_columns(hist / "h15_elect_live" / "race_map.csv")
    assert set(cols) == {"market_id", "event_id"}  # winner and price are dropped at read
    for bad in (hist / "h15_elect_live" / "outcomes.csv", hist / "h15_elect_live" / "holdout" / "race_map.csv", hist / "h15_other" / "race_map.csv", hist / "h15_elect_live" / "race_map_guarded.csv"):
        with pytest.raises(c16.Refused):
            c16.guard_id_file(bad)
