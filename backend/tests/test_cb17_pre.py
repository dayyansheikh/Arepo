# ruff: noqa: E501
"""CB17 part ``pre`` rules (offline, pure): branch rule, strata ladders and level selection, cut points and their causality, the SE-only planning recipe, the cost map, rules hashing, refusals."""

from __future__ import annotations

import json
import math

import numpy as np
import pytest

from astrolabe.research_lab import cb17_common as c17
from astrolabe.research_lab import cb17_pre as pre

# ---- rules file: staged parts, determinism, tamper ----------------------------------------------------------------------------------------------


@pytest.fixture()
def rules_file(tmp_path):
    p = tmp_path / "cb17_rules.json"
    c17.write_rules(p)
    return p


def test_part_pre_unchanged_later_parts_declared_and_a_withdrawn(rules_file):
    """After q0400-q0403 (section 11): pre keeps its hash, common / B / C / E are declared, A is withdrawn uncounted (branch T) and never declared."""
    doc = json.loads(rules_file.read_text())
    assert doc["rules_version"] == "cb17-rules-v1" and set(doc["parts"]) == {"common", "pre", "A", "B", "C", "E"}
    assert doc["parts"]["pre"]["part_declared"] is True and doc["parts"]["pre"]["rules_sha256"] == "ddc0249b23eedf8cfe50b2b60e94378264804ca4791c82c01cf3993df54df6a7"
    assert doc["parts"]["pre"]["modules"] == ["cb17_common", "cb17_pre", "cb17_census"]
    for p in ("common", "B", "C", "E"):
        assert doc["parts"][p]["part_declared"] is True and c17.verify_rules(rules_file, require_committed=False, part=p) == doc["parts"][p]["rules_sha256"]
    assert doc["parts"]["A"]["part_declared"] is False and doc["parts"]["A"]["rules_sha256"] is None
    with pytest.raises(c17.Refused, match="not declared"):
        c17.verify_rules(rules_file, require_committed=False, part="A")
    assert c17.verify_rules(rules_file, require_committed=False, part="pre") == doc["parts"]["pre"]["rules_sha256"]


def test_rules_hash_is_deterministic_and_independent_of_the_staging_switches(monkeypatch):
    a = c17.rules_part_file_doc("pre")["rules_sha256"]
    assert a == c17.rules_part_file_doc("pre")["rules_sha256"] and len(a) == 64
    # declaring a later part edits only the lower-case staging switches: part pre must keep its hash
    monkeypatch.setattr(c17, "_declared_parts", ("pre", "common"))
    assert c17.rules_part_file_doc("pre")["rules_sha256"] == a


def test_rules_tamper_is_detected_and_a_declared_part_is_never_rewritten(rules_file, tmp_path):
    doc = json.loads(rules_file.read_text())
    doc["parts"]["pre"]["constants"]["cb17_pre"]["AGREE_MIN_PCT"] = 90
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(doc))
    with pytest.raises(c17.Refused, match="hash mismatch"):
        c17.verify_rules(bad, require_committed=False, part="pre")
    doc2 = json.loads(rules_file.read_text())
    doc2["parts"]["pre"]["rules_sha256"] = "0" * 64
    rules_file.write_text(json.dumps(doc2))
    with pytest.raises(c17.Refused, match="never rewritten"):
        c17.write_rules(rules_file)


def test_rules_constants_pin_the_design_numbers():
    d = c17.rules_part_doc("pre")["constants"]
    assert d["cb17_pre"]["AGREE_MIN_PCT"] == 97 and d["cb17_pre"]["WILSON_LOWER_MIN"] == 0.95 and d["cb17_pre"]["AGREE_N_MIN"] == 800 and d["cb17_pre"]["CELL_N_MIN"] == 100
    assert d["cb17_pre"]["SELECT_SHARE_MIN"] == 0.60 and d["cb17_pre"]["TRAILING_MIN_PRIOR"] == 6 and d["cb17_pre"]["COST_SIZES_USD"] == [1000.0, 5000.0]
    assert d["cb17_common"]["CENSUS_CUTOFF"] == "2026-10-16T00:00:00Z" and d["cb17_common"]["LOOKBACK_FLOOR"] == "2026-10-26T00:00:00Z" and d["cb17_common"]["DATA_DUMPS_CAP_GB"] == 40.0
    assert c17.MDE_FACTOR == 3.80


# ---- the branch rule (section 10.4 item 2) ------------------------------------------------------------------------------------------------------


def ok_cells(n=400, k=400):
    return {"touch_age": {"0-20min": {"n": n, "k": k}, "20-60min": {"n": n, "k": k}}, "p_band": {"P[0.20,0.80]": {"n": n, "k": k}}, "class": {"PATH-SETTLED": {"n": n, "k": k}}}


def test_wilson_lower_bound_and_the_integer_97_percent_edge():
    assert pre.wilson_lower(0, 0) == 0.0
    assert pre.wilson_lower(97, 100) < 0.95 < pre.wilson_lower(776, 800)
    assert pre.wilson_lower(776, 800) == pytest.approx(0.9565, abs=2e-3)
    # exactly 97% passes, one fewer fails (no float edge)
    assert pre.agreement_rule({"n": 800, "k": 776}, ok_cells())["pass"] is True
    r = pre.agreement_rule({"n": 800, "k": 775}, ok_cells())
    assert r["pass"] is False and any("below 97%" in x for x in r["reasons"])


def test_branch_rule_requires_n_800_and_wilson_and_every_cell_with_n_100():
    assert pre.agreement_rule({"n": 799, "k": 799}, ok_cells())["pass"] is False  # n < 800
    assert pre.agreement_rule({"n": 800, "k": 800}, ok_cells())["pass"] is True
    # a failing band at n = 100 binds; the same band at n = 99 is reported only
    failing = ok_cells()
    failing["touch_age"]["20-60min"] = {"n": 100, "k": 96}
    r = pre.agreement_rule({"n": 971, "k": 960}, failing)
    assert r["pass"] is False and r["cells"]["touch_age:20-60min"]["binding"] is True and any("touch_age:20-60min" in x for x in r["reasons"])
    small = ok_cells()
    small["touch_age"]["20-60min"] = {"n": 99, "k": 90}
    r = pre.agreement_rule({"n": 971, "k": 960}, small)
    assert r["pass"] is True and r["cells"]["touch_age:20-60min"] == {"n": 99, "agree": 90, "binding": False, "ok": None}
    # the Wilson bound is a separate criterion
    assert any("Wilson" in x for x in pre.agreement_rule({"n": 800, "k": 776}, ok_cells())["reasons"]) is False


def test_branch_decision_s_t_and_not_run():
    s = pre.branch_decision({"n": 971, "k": 960}, ok_cells())
    assert s["branch"] == "S" and s["pass"] and s["consequence"] is None
    t = pre.branch_decision({"n": 971, "k": 900}, ok_cells())
    assert t["branch"] == "T" and "withdrawn uncounted" in t["consequence"]
    nr = pre.branch_decision(None, None)
    assert nr["branch"] == "T" and "did not run" in nr["reasons"][0]
    assert pre.branch_decision({"n": 0, "k": 0}, {})["branch"] == "T"
    assert "GAS" in pre.GAS_RULE_TEXT and "NOT implemented" in pre.GAS_RULE_TEXT


def test_bands_and_edges():
    assert [pre.p_band(x) for x in (0.02, 0.03, 0.1999, 0.20, 0.80, 0.8001, 0.97, 0.98)] == [None, 0, 0, 1, 1, 2, 2, None]
    assert [pre.touch_age_band(x) for x in (0, 1199, 1200, 3600, 3601, -1)] == [0, 0, 1, 1, None, None]
    assert [pre.spread_band(x) for x in (0.01, 0.02, 0.05, 0.0501)] == [0, 1, 2, 3] and [pre.spread_2band(x) for x in (0.02, 0.0201)] == [0, 1]
    assert [pre.size_band(x) for x in (2499, 2500, 9999, 10000)] == [0, 1, 1, 2] and [pre.abs_dm_band(x) for x in (1.0, 1.01, 3.0, 3.01)] == [0, 1, 1, 2]


# ---- strata ladders, informativeness, level selection (section 2.6) -----------------------------------------------------------------------------


def test_strata_keys_by_family_and_level():
    a = {"p": 0.5, "size_usd": 3000, "ts": 1760227800.0, "spread": 0.03}
    assert pre.stratum("A", 0, a) == (1, 1, c17.band6(a["ts"]), 2) and pre.stratum("A", 1, a) == (1, 1) and pre.stratum("A", 2, a) == (1,)
    b1 = {"ts": 1760227800.0, "spread": 0.005, "act": 2, "reward": 1}
    assert len(pre.stratum("B1", 0, b1)) == 4 and pre.stratum("B1", 1, b1) == (2, c17.utc_hour(b1["ts"]) // 12, 0) and pre.stratum("B1", 2, b1) == (2,)
    b2 = {**b1, "imb": 1}
    assert len(pre.stratum("B2", 0, b2)) == 4 and pre.stratum("B2", 1, b2) == (2, 1) and pre.stratum("B2", 2, b2) == (1,)
    c = {"ts": 1760227800.0, "abs_dm_c": 2.0, "dv_tercile": 1, "dv_above": 1, "n_moving": 3}
    assert pre.stratum("C", 0, c) == (c17.band6(c["ts"]), 1, 1, 2) and pre.stratum("C", 1, c) == (1, 1) and pre.stratum("C", 2, c) == (1,)
    with pytest.raises(c17.Refused):
        pre.stratum("A", 3, a)
    with pytest.raises(c17.Refused):
        pre.stratum("Z", 0, a)


def test_informativeness_definitions():
    # binary: cells holding both labels / all units
    r = pre.informativeness_binary([("a", 1), ("a", 0), ("b", 1), ("b", 1), ("c", 0)])
    assert r == {"numerator": 2, "denominator": 5, "share": 0.4}
    # continuous: >= 2 units and x not constant
    r = pre.informativeness_continuous([("a", 1.0), ("a", 2.0), ("b", 1.0), ("b", 1.0), ("c", 3.0)])
    assert r["numerator"] == 2 and r["denominator"] == 5
    # three classes: transfer vs mint-heavy; merge-heavy outside the share
    r = pre.informativeness_three_class([("a", "transfer"), ("a", "mint"), ("a", "merge"), ("b", "transfer"), ("b", "merge"), ("c", "mint")])
    assert r["numerator"] == 2 and r["denominator"] == 4 and r["share"] == 0.5 and r["merge_units_reported"] == 2
    assert pre.informativeness_binary([])["share"] is None


def test_level_selection_at_the_60_percent_edge():
    assert pre.select_level({0: 0.5999, 1: 0.6, 2: 0.9})["selected_level"] == 1
    assert pre.select_level({0: 0.6, 1: 0.9, 2: 1.0})["selected_level"] == 0
    assert pre.select_level({0: 0.1, 1: 0.2, 2: 0.5999}) == {"selected_level": 2, "reason": pre.select_level({0: 0.1, 1: 0.2, 2: 0.5999})["reason"], "fallback": True}
    assert pre.select_level({0: None, 1: None, 2: None})["selected_level"] == 2
    assert pre.select_level({0: None, 1: 0.7})["selected_level"] == 1


def test_level_report_picks_the_finest_informative_level_from_features_only():
    # A units: (market, d) cell; level 2 (P band) cells hold both labels, level 0 (144 strata) splits them apart.
    units = []
    for i in range(40):
        units.append({"market": "m1", "d": 1, "open": i % 2, "p": 0.5, "size_usd": 1000.0 + 3000.0 * (i % 4), "ts": 1760227800.0 + 6 * 3600 * (i % 4), "spread": 0.005 + 0.015 * (i % 3)})
    rep = pre.level_report("A", units, lambda u: (u["market"], u["d"]), lambda u: u["open"])
    shares = {k: v["share"] for k, v in rep["levels"].items()}
    assert shares["level2"] == 1.0 and shares["level1"] >= shares["level0"] and rep["selected_level"] == next(lv for lv in (0, 1, 2) if shares[f"level{lv}"] >= 0.6)
    # a callable source is re-iterated per level
    rep2 = pre.level_report("A", lambda: iter(units), lambda u: (u["market"], u["d"]), lambda u: u["open"])
    assert rep2["selected_level"] == rep["selected_level"]
    # no level reaches 60%: level 2 with the window's 50% rule binding
    lone = [{"market": f"m{i}", "d": 1, "open": i % 2, "p": 0.5, "size_usd": 100.0, "ts": 1760227800.0, "spread": 0.01} for i in range(10)]
    r3 = pre.level_report("A", lone, lambda u: (u["market"], u["d"]), lambda u: u["open"])
    assert r3["selected_level"] == 2 and r3["fallback"] is True


# ---- cut points and their causality (finding 6) -------------------------------------------------------------------------------------------------


def test_tercile_cuts_and_classes():
    assert pre.tercile_cuts([1, 2]) is None and pre.tercile_cuts([float("nan")] * 5) is None
    lo, hi = pre.tercile_cuts(range(1, 10))
    assert (lo, hi) == (pytest.approx(3.6667, abs=1e-3), pytest.approx(6.3333, abs=1e-3))
    assert [pre.tercile_of(x, (lo, hi)) for x in (1, lo, 5, hi, 9)] == [0, 0, 1, 1, 2]
    assert [pre.c_class(x, (1.0, 2.0)) for x in (0.5, 1.0, 1.5, 2.0, 2.5)] == ["merge", "transfer", "transfer", "transfer", "mint"]


def test_trailing_cuts_need_six_prior_and_ignore_the_current_value():
    assert pre.trailing_cuts([1, 2, 3, 4, 5]) is None
    prior = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    cuts = pre.trailing_cuts(prior)
    assert cuts == pre.tercile_cuts(prior)
    # the cut points are a function of the prior list alone: a huge current r_k cannot move them
    assert pre.trailing_cuts(list(prior)) == cuts and pre.c_class(1e9, cuts) == "mint"
    assert pre.trailing_dv([1, 2, 3], 5) is None
    t = pre.trailing_dv(prior, 5.5)
    assert t[0] in (0, 1, 2) and t[1] == 1 and pre.trailing_dv(prior, 1.0) == (0, 0)


# ---- planning SE: SEs only, FE cancels unit constants ------------------------------------------------------------------------------------------


def _se_world(rng, shift=0.0, n_units=40, per=12):
    y, x, fe, ev, blk = [], [], [], [], []
    for u in range(n_units):
        c0 = rng.normal(0, 5.0) + shift
        for k in range(per):
            lab_ = float(k % 2)
            y.append(c0 + rng.normal(0, 1.0))
            x.append(lab_)
            fe.append(f"u{u}")
            ev.append(f"e{u // 2}")
            blk.append(k)
    return y, x, fe, {"event": ev, "block6": blk}


def test_planning_se_returns_no_point_estimate_and_fe_cancels_unit_constants():
    rng = np.random.default_rng(1)
    y, x, fe, ways = _se_world(rng)
    out = pre.fe_cluster_se(y, x, fe, ways)
    assert set(out) <= {"n", "se", "mde", "se_by_way", "g_by_way", "recipe", "note", "mde_over_power_gate"} and out["se"] > 0
    assert out["mde"] == pytest.approx(3.80 * out["se"], abs=1e-5)
    assert not any(k.lower().split("_", 1)[0] in c17.OUTCOME_KEY_TOKENS for k in out)
    # a per-unit constant added to y changes nothing (fixed effects)
    shifted = [v + 100.0 * int(f[1:]) for v, f in zip(y, fe, strict=True)]
    out2 = pre.fe_cluster_se(shifted, x, fe, ways)
    assert out2["se"] == pytest.approx(out["se"], rel=1e-6)
    c17.assert_clean_result(out)


def test_planning_se_degenerate_inputs_do_not_raise():
    assert pre.fe_cluster_se([1.0, 2.0], [0.0, 1.0], ["a", "a"], {"event": ["e", "e"]})["se"] is None
    flat = pre.fe_cluster_se([1.0] * 6, [1.0] * 6, ["a", "a", "b", "b", "c", "c"], {"event": list("xxyyzz")})
    assert flat["se"] is None and "rank deficient" in flat.get("note", "")


# ---- cost-map recipe -----------------------------------------------------------------------------------------------------------------------------


def test_round_trip_cost_walks_the_depth_bands_and_is_none_when_it_does_not_fit():
    assert pre.walk_edge(100, 500, 2000) == 0.01 and pre.walk_edge(600, 500, 2000) == 0.05 and pre.walk_edge(3000, 500, 2000) is None and pre.walk_edge(0, 1, 1) is None
    c = pre.round_trip_cost_c(0.49, 0.51, 5000, 9000, 5000, 9000, 1000.0, 0.0)
    assert c == pytest.approx(100.0 * (0.52 - 0.48), abs=1e-6)
    cf = pre.round_trip_cost_c(0.49, 0.51, 5000, 9000, 5000, 9000, 1000.0, 0.04)
    assert cf > c
    assert pre.round_trip_cost_c(0.49, 0.51, 100, 200, 100, 200, 5000.0, 0.0) is None  # does not fit within 5c
    assert pre.round_trip_cost_c(0.51, 0.49, 5000, 9000, 5000, 9000, 1000.0, 0.0) is None  # crossed
    assert pre.round_trip_cost_c(math.nan, 0.5, 1, 1, 1, 1, 1.0, 0.0) is None


def test_hist_streaming_quantiles():
    h = pre.Hist(1.0, 100.0)
    for v in range(1, 101):
        h.add(float(v))
    h.add(math.nan)
    assert h.n == 100 and h.quantile(0.5) == pytest.approx(50.0, abs=1.0) and h.share_gt(90.0) == pytest.approx(0.10, abs=0.02)
    assert pre.Hist(1.0, 10.0).quantile(0.5) is None and pre.Hist(1.0, 10.0).summary()["n"] == 0


# ---- refusals: census window, holdout, lookback floor, refused roots, forbidden result keys -----------------------------------------------------


def test_census_cutoff_refuses_rows_at_or_after_2026_10_16():
    cut = c17.census_cutoff()
    assert c17.guard_census_time(cut - 1.0) == cut - 1.0
    for bad in (cut, cut + 1.0, c17.ep("2026-10-26T00:00:00Z"), math.nan):
        with pytest.raises(c17.Refused):
            c17.guard_census_time(bad)


def test_lookback_floor_refuses_pre_floor_rows_for_window_readers():
    floor = c17.ep(c17.LOOKBACK_FLOOR)
    assert c17.guard_not_window(floor) == floor
    for bad in (floor - 1.0, floor - 2 * 3600.0, c17.ep("2026-10-21T00:00:00Z"), math.nan):  # S_8 - 2 h, J4-R and CB13-T HOLDOUT days
        with pytest.raises(c17.Refused, match="lookback floor"):
            c17.guard_not_window(bad)


def test_holdout_and_other_batch_paths_are_refused(tmp_path):
    for p in (tmp_path / "creative_batch13" / "t_holdout" / "fills.csv.gz", tmp_path / "x" / "holdout" / "a", tmp_path / "creative_batch13" / "t_screen" / "holdout_fills.csv.gz"):
        with pytest.raises(c17.Refused, match="HOLDOUT"):
            c17.refuse_path(p, allow=("creative_batch13",))
    with pytest.raises(c17.Refused, match="refused root"):
        c17.refuse_path(tmp_path / "creative_batch16" / "smoke.json")
    with pytest.raises(c17.Refused):
        c17.refuse_path(tmp_path / "surprise_live" / "x")
    # a census may open only the two worn SCREEN tables
    d = tmp_path / "creative_batch13" / "t_screen"
    assert c17.guard_cb13_t_screen_file(d / "fills.csv.gz") == d / "fills.csv.gz"
    for bad in (d / "marks.csv.gz", tmp_path / "creative_batch13" / "t_holdout" / "fills.csv.gz", tmp_path / "creative_batch13" / "fills.csv.gz", tmp_path / "creative_batch12" / "t_screen" / "fills.csv.gz"):
        with pytest.raises(c17.Refused):
            c17.guard_cb13_t_screen_file(bad)


def test_monitor_and_directory_guards(tmp_path):
    lt = tmp_path / "live_trades"
    for day in c17.CENSUS_DAYS:
        c17.guard_monitor_file(lt / f"trades-{day}.jsonl")
    for bad in ("trades-20261016.jsonl", "trades-20261011.jsonl", "scores-20261012.jsonl", "alerts.jsonl", "outcomes.jsonl", "wallets.jsonl", "stats.jsonl", "state.json", "trades-20261012.jsonl.gz"):
        with pytest.raises(c17.Refused):
            c17.guard_monitor_file(lt / bad)
    with pytest.raises(c17.Refused):
        c17.guard_monitor_file(tmp_path / "elsewhere" / "trades-20261012.jsonl")
    snaps, sweeps = tmp_path / "snapshots", tmp_path / "book_sweeps"
    d, t = c17.guard_capture_dir(snaps / "20261012T003103Z_2df48d64")
    assert t == c17.ep("2026-10-12T00:31:03Z")
    with pytest.raises(c17.Refused, match="cut-off"):
        c17.guard_capture_dir(snaps / "20261016T000000Z_2df48d64")
    with pytest.raises(c17.Refused, match="before the census window"):
        c17.guard_capture_dir(snaps / "20261011T210000Z_2df48d64")
    c17.guard_capture_dir(snaps / "20261011T230000Z_2df48d64", c17.CAPTURE_LOOKBACK_START)  # q0400's touch lookback only
    with pytest.raises(c17.Refused):
        c17.guard_sweep_dir(sweeps / "20261026T000000Z_ab12cd34")
    with pytest.raises(c17.Refused):
        c17.guard_sweep_dir(tmp_path / "other" / "20261012T000000Z_ab12cd34")


def test_output_root_and_clean_result_rules(tmp_path):
    c17.require_output_root(tmp_path / "creative_batch17" / "x.json")
    for bad in (tmp_path / "x.json", tmp_path / "creative_batch16" / "x.json", tmp_path / "creative_batch17" / "holdout" / "x.json"):
        with pytest.raises(c17.Refused):
            c17.require_output_root(bad)
    c17.assert_clean_result({"counts": {"a": 1}, "se": 0.1, "mde": 0.4, "list": [{"n": 1}], "markets": 3, "markets_in_static_index": 4, "next_pass_no_mark_by_age_bin": {}, "network": 1})
    for bad in ({"beta": 1}, {"x": {"mark_out": 1}}, {"x": [{"net_cents": 1}]}, {"estimate": 1}, {"outcome_share": 1}, {"wallet_x": 1}, {"side": "BUY"}, {"recv_ts": 1}, {"pnl": 1}, {"coef": 1}, {"effect_size": 1}, {"tx16": "a"}):
        with pytest.raises(c17.Refused, match="forbidden key"):
            c17.assert_clean_result(bad)
    out = tmp_path / "creative_batch17" / "r.json"
    sha = c17.write_result_once(out, {"n": 1})
    assert len(sha) == 64 and out.exists()
    with pytest.raises(Exception):  # noqa: B017  (write-once)
        c17.write_result_once(out, {"n": 2})
    with pytest.raises(c17.Refused):
        c17.write_result_once(tmp_path / "creative_batch17" / "bad.json", {"mark": 1})


def test_event_arm_style_helpers_are_deterministic():
    assert c17.sha256_obj({"a": 1, "b": [1, 2]}) == c17.sha256_obj({"b": [1, 2], "a": 1})
    assert c17.block6(c17.ep("2026-10-12T05:59:59Z")) + 1 == c17.block6(c17.ep("2026-10-12T06:00:00Z")) and [c17.band6(c17.ep(f"2026-10-12T{h:02d}:00:00Z")) for h in (0, 5, 6, 12, 18, 23)] == [0, 0, 1, 2, 3, 3]
