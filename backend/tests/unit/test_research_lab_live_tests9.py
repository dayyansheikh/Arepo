# ruff: noqa: E501
"""LT9 (LIVE_TESTS_9.md) code phase 1: the vendored base's provenance, the end-date parse rule, the feed reader and clock, the reward carry and the
omission state, CH213's break, cell rule, panel and relpos (re-check fix 6), CH214's split at zero (re-check fix 2), CH212's route-A end rule
(re-check fix 3) and route rule, CH215's decision-order control assignment (re-check fix 1) and clusters, the lag-slot loaders, the MDE
arithmetic against the design text, the fresh seal and its refusals, the three sealed censuses end to end on a synthetic host tree, causality,
ops-stats and the runner. Synthetic data only; no network; no target is formed."""

from __future__ import annotations

import ast
import copy
import gzip
import hashlib
import importlib.util
import json
import math
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import live_tests7_base as l7b
from astrolabe.research_lab import live_tests8 as l8
from astrolabe.research_lab import live_tests9 as lt
from astrolabe.research_lab import live_tests9_base as b

HERE = Path(lt.__file__).resolve().parent
G0 = datetime(2026, 10, 1, 0, 31, tzinfo=UTC)
N_MKT = 48
SPAN = (14, 37)  # synthetic census span (slots); captures 2..39, sweeps 12..39


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _slot_dt(k: int) -> datetime:
    return G0 + timedelta(hours=2 * k)


# --- vendored provenance -----------------------------------------------------------------------------------------------------------


def test_vendored_provenance():
    text = (HERE / "live_tests9_base.py").read_text()
    tree = ast.parse(text)
    nodes = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    drift = lt.load_spec(sha=None)["vendored_source_drift_accepted"]
    assert len(b.VENDORED) >= 120
    cur = {f: (HERE / f).read_text() for f in ("live_tests7.py", "live_tests7_base.py", "live_tests8.py")}
    for name, v in b.VENDORED.items():
        copy_src = ast.get_source_segment(text, nodes[name])
        assert hashlib.sha256(copy_src.encode()).hexdigest() == v["normalised_sha256"], name
        f = v["source"]
        sha_now = hashlib.sha256(cur[f].encode()).hexdigest()
        if sha_now != v["source_sha256"]:
            assert f in drift and drift[f]["sha256"] == sha_now, f"{f} drifted without a vendored_source_drift_accepted entry"
        node = next(n for n in ast.parse(cur[f]).body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == name)
        assert re.sub(v["prefix"], "", ast.get_source_segment(cur[f], node)) == copy_src, f"{name} differs from its current source"
        if "origin" in v:
            assert l7b.VENDORED[name]["normalised_sha256"] == v["origin"]["normalised_sha256"] == v["normalised_sha256"]
    assert b.VENDORED["RewardCarry"]["source_sha256"].startswith("e1c5c0c6") and b.VENDORED["_status_array"]["source"] == "live_tests7.py"
    assert b.VENDORED["reward_detail"]["source_sha256"].startswith("d1b252cf")


def test_no_lt9_module_imports_lt3_to_lt8():
    for p in (*HERE.glob("live_tests9*.py"), HERE.parents[1] / "scripts" / "run_live_tests9.py", HERE.parents[1] / "scripts" / "vendor_lt9_base.py"):
        for node in ast.walk(ast.parse(p.read_text())):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [(node.module or "")] + [a.name for a in node.names]
            for n in names:
                assert not re.search(r"live_tests[3-8]", n), f"{p.name} imports {n}"


def test_copied_constants_equal_their_sources():
    for c in ("GRID_S", "SLOT_TOL_S", "DAY_S", "SNAP_COLS", "EXT_COLS", "SWEEP_COLS"):
        assert getattr(b, c) == getattr(l7b, c), c
    assert b.LT7_STATUS == l8.LT7_STATUS and b.RW_COLS == l8.RW_COLS and b._NULL_LIKE == l8._NULL_LIKE
    assert b.REWARD_CARRY_SLOTS == 12


def test_vendor_script_refuses_other_hashes(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("vendor_lt9", HERE.parents[1] / "scripts" / "vendor_lt9_base.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.SOURCE_PINS["live_tests7.py"].startswith("e1c5c0c6") and mod.SOURCE_PINS["live_tests7_base.py"].startswith("2e8baa90")
    monkeypatch.setattr(mod, "SOURCE_PINS", {**mod.SOURCE_PINS, "live_tests8.py": "0" * 64})
    monkeypatch.setattr(mod, "OUT", tmp_path / "out.py")
    with pytest.raises(SystemExit, match="refusing"):
        mod.main()
    assert not (tmp_path / "out.py").exists()


def test_design_text_sha_constant_and_f_roles_fixed():
    assert lt.DESIGN_TEXT_SHA256.startswith("098aa3fb")
    spec = lt.load_spec(sha=None)
    assert [lt.f_role(spec, t) for t in lt.TESTS] == ["binding", "binding", "label", "placebo"]
    bad = copy.deepcopy(spec)
    bad["f_roles"]["CH213"] = "label"
    with pytest.raises(RuntimeError):
        lt.f_role(bad, "CH213")
    bad2 = copy.deepcopy(spec)
    bad2["f_binding"] = {"CH212": True}
    with pytest.raises(RuntimeError):
        lt.f_role(bad2, "CH212")


# --- the end-date parse rule (1.2, re-check fix 3) and the feed -------------------------------------------------------------------------


@pytest.mark.parametrize("v,kind,lo", [
    ("2026-11-05", "date_only", "2026-11-05T00:00:00Z"), ("2026-11-05T12:00:00+02:00", "ts", "2026-11-05T10:00:00Z"), ("2026-11-05T12:00:00", "ts", "2026-11-05T12:00:00Z"),
    ("2026-11-05T12:00:00Z", "ts", "2026-11-05T12:00:00Z"), ("2199-01-01", "sentinel", None), ("2500-06-01T00:00:00Z", "sentinel", None), (None, "open", None), ("", "open", None),
    ("null", "open", None), ("2019-12-31", "malformed", None), ("2019-12-31T23:00:00Z", "malformed", None), ("soon", "malformed", None), (1793836800, "malformed", None), ("2026-13-40", "malformed", None),
])
def test_parse_end_rule(v, kind, lo):
    a, z, k = lt.parse_end(v)
    assert k == kind
    if lo is None:
        assert math.isnan(a)
    else:
        assert a == lt.epoch(lo)
        assert z == (a + 86400.0 if kind == "date_only" else a)


def _feed_dir(root: Path, name: str, recs: list[dict], state: str = "complete", start: datetime | None = None, rows: bool = True) -> Path:
    d = root / name
    d.mkdir(parents=True)
    start = start or datetime(2026, 10, 2, tzinfo=UTC)
    if rows:
        with gzip.open(d / "rows.jsonl.gz", "wt") as fh:
            for r in recs:
                fh.write(json.dumps(r) + "\n")
    (d / "manifest.json").write_text(json.dumps({"state": state, "started_utc": _iso(start), "finished_utc": _iso(start + timedelta(minutes=1))}))
    return d


def test_feed_frame_end_aggregation(tmp_path):
    spec = lt.load_spec(sha=None)
    recs = [{"feed": "native", "condition_id": "a", "rewards_max_spread": 3.5, "rewards_min_size": 20, "rewards_config": [{"rate_per_day": 5, "end_date": "2026-11-05"}, {"rate_per_day": 2, "end_date": "2026-11-06T06:00:00Z"}]},
            {"feed": "sponsored", "condition_id": "a", "rewards_config": [{"rate_per_day": 1, "end_date": "2026-11-04"}]},
            {"feed": "native", "condition_id": "b", "rewards_config": [{"rate_per_day": 5, "end_date": None}, {"rate_per_day": 5, "end_date": "2026-11-01"}]},
            {"feed": "native", "condition_id": "c", "rewards_config": [{"rate_per_day": 5, "end_date": "junk"}]},
            {"feed": "native", "condition_id": "d", "rewards_config": [{"rate_per_day": 0, "end_date": "2026-11-05"}]},
            {"feed": "native", "condition_id": "e", "rewards_config": [{"rate_per_day": 5, "end_date": "2300-01-01"}]}]
    f = lt.feed_frame(_feed_dir(tmp_path, "f1", recs), spec)
    assert f.loc["a", "feeds"] == "both" and f.loc["a", "rate"] == 8 and f.loc["a", "end_kind"] == "dated"
    assert f.loc["a", "end_lo"] == lt.epoch("2026-11-06T06:00:00Z") and f.loc["a", "n_date_only"] == 2
    assert f.loc["b", "end_kind"] == "open" and f.loc["c", "end_kind"] == "malformed" and f.loc["d", "end_kind"] == "none" and f.loc["e", "end_kind"] == "open"
    assert f.loc["e", "n_sentinel"] == 1


def test_feed_clock_skips_failed_and_uses_finish_before_start(tmp_path):
    t = datetime(2026, 10, 5, 10, 35, tzinfo=UTC)
    _feed_dir(tmp_path, "f_ok", [{"condition_id": "x"}], start=t)
    _feed_dir(tmp_path, "f_fail", [{"condition_id": "x"}], state="failed", start=t + timedelta(minutes=30))
    _feed_dir(tmp_path, "f_late", [{"condition_id": "x"}], start=t + timedelta(hours=2))
    feeds = lt.scan_feed([tmp_path])
    assert not feeds["f_fail"]["usable"]
    cap_start = lt.epoch("2026-10-05T12:31:00Z")
    assert lt.last_usable_before(feeds, cap_start) == "f_ok"
    assert lt.last_usable_before(feeds, lt.epoch("2026-10-05T10:36:00Z")) is None  # finish 10:36 is not EARLIER than 10:36
    assert lt.last_usable_before(feeds, lt.epoch("2026-10-05T14:31:00Z")) == "f_late"


def test_route_a_end_rule_at_slot_k_plus_2_nominal_start():
    spec = lt.load_spec(sha=None)
    k = 100
    t2 = lt.b.slot_time(k + 2, spec)
    f = pd.DataFrame({"end_kind": ["dated", "dated", "dated", "open", "malformed", "none"], "end_lo": [t2 + 1, t2, t2 - 3600, np.nan, np.nan, np.nan]},
                     index=pd.Index(["a", "b", "c", "d", "e", "g"], name="condition_id"))
    ok, why = lt.feed_end_ok(pd.Series(["a", "b", "c", "d", "e", "g"]), f, k, spec)
    assert list(ok[:4]) == [1.0, 0.0, 0.0, 1.0] and np.isnan(ok[4]) and np.isnan(ok[5])
    assert list(why) == ["", "feed_end_soon", "feed_end_soon", "feed_end_open", "feed_end_malformed", "feed_no_positive_config"]
    # a date-only D is taken at D 00:00Z (the earliest consistent instant): D = the day of slot k + 2 is NOT after it
    d = datetime.fromtimestamp(t2, UTC).strftime("%Y-%m-%d")
    lo, _, kind = lt.parse_end(d)
    assert kind == "date_only" and lo < t2
    ok2, _ = lt.feed_end_ok(pd.Series(["z"]), pd.DataFrame({"end_kind": ["dated"], "end_lo": [lo]}, index=pd.Index(["z"], name="condition_id")), k, spec)
    assert ok2[0] == 0.0
    okm, whym = lt.feed_end_ok(pd.Series(["a"]), None, k, spec)
    assert np.isnan(okm[0]) and whym[0] == "feed_missing"


def test_feed_flags_listed_and_dropped():
    fk = pd.DataFrame(index=pd.Index(["a"], name="condition_id"))
    fp = pd.DataFrame(index=pd.Index(["a", "b"], name="condition_id"))
    r = lt.feed_flags(pd.Series(["a", "b", "c"]), fk, fp)
    assert list(r["clob_listed"]) == [1, 0, 0] and list(r["clob_dropped"]) == [0, 1, 0]
    r2 = lt.feed_flags(pd.Series(["a"]), None, fp)
    assert np.isnan(r2["clob_listed"][0]) and np.isnan(r2["clob_dropped"][0])


# --- reward carry and the omission state (1.4.1) ------------------------------------------------------------------------------------


def _rwf(rows: dict[str, str | None], day="2026-10-05") -> pd.DataFrame:
    ext = pd.DataFrame({"market_id": list(rows), "clob_rewards": list(rows.values()), "rewards_min_size": "20", "rewards_max_spread": "3.5"}).set_index("market_id")
    ext.attrs["has_clob_rewards"] = True
    return b.rw_frame(ext, day).set_index("market_id")


def _serf(status: dict[str, str], rate: dict[str, float]) -> pd.DataFrame:
    return pd.DataFrame({"rew_status": list(status.values()), "rew_rate": [rate[m] for m in status], "rew_min": 20.0, "rew_maxspread": 3.5},
                        index=pd.Index(list(status), name="market_id"))


LISTED = '[{"startDate":"2026-01-01","endDate":"2027-01-01","rewardsDailyRate":10}]'
INACTIVE = '[{"startDate":"2026-01-01","endDate":"2026-02-01","rewardsDailyRate":10}]'


def test_carry_frame_om_from_carry_lag_and_nothing_after_k():
    c = b.RewardCarry(12)
    c.add(10, _rwf({"m1": LISTED, "m2": LISTED, "m3": INACTIVE, "m4": None}))
    c.add(11, _rwf({"m1": None, "m2": LISTED, "m3": None, "m4": None}))
    c.add(13, _rwf({"m1": LISTED, "m2": LISTED, "m3": LISTED, "m4": LISTED}))  # a LATER slot: must be ignored at k = 12
    ser = _serf({"m1": "null", "m2": "listed", "m3": "null", "m4": "null"}, {"m1": 0.0, "m2": 10.0, "m3": 0.0, "m4": 0.0})
    f = lt.carry_frame(c, ser, 12, "2026-10-05")
    assert list(f["rewarded"]) == [1.0, 1.0, 0.0, 0.0]  # m3: listed-inactive in the window -> 0; m4: never listed -> 0
    assert f.loc["m1", "carry_lag"] == 2 and f.loc["m2", "carry_lag"] == 0 and f.loc["m1", "om"] == 1 and f.loc["m2", "om"] == 0
    assert np.isnan(f.loc["m3", "om"])
    ser_nan = ser.assign(rew_status=[np.nan, "listed", "malformed", "absent"])  # a 'null' cell read back from CSV as NaN is null (_status_array)
    f2 = lt.carry_frame(c, ser_nan, 12, "2026-10-05")
    assert f2.loc["m1", "om"] == 1 and np.isnan(f2.loc["m3", "rewarded"]) and np.isnan(f2.loc["m4", "rewarded"])


# --- CH213 (design 2) -----------------------------------------------------------------------------------------------------------------


def test_break_flag_edges():
    # v = 2c: 2v = 4c. s_{k-1} just below 4c and s_k exactly 4c is a break; s_{k-1} exactly 4c is not
    f = lt.break_flag([3.999, 4.0, 3.0, 3.0, np.nan], [4.0, 5.0, 3.999, 9.0, 5.0], [2.0, 2.0, 2.0, 2.0, 2.0])
    assert list(f[:4]) == [1.0, 0.0, 0.0, 1.0] and np.isnan(f[4])
    assert lt.break_flag([0.03 * 100], [0.06 * 100], [3.0])[0] == 1.0  # float noise of 0.06 - 0.00 in cents


def _cell_frame(n_cell: int, n_tt: int) -> pd.DataFrame:
    rows = []
    for i in range(n_cell):
        rows.append({"market_id": f"r{i}", "fee_cat": "Politics", "liq": 5e4, "tick": 0.01, "rew_maxspread": 3.0 + (i % 3), "rewarded": 1.0, "n_members": 50.0})
    for i in range(n_tt):
        rows.append({"market_id": f"t{i}", "fee_cat": "Economy", "liq": 5e4, "tick": 0.01, "rew_maxspread": 1.5, "rewarded": 1.0, "n_members": 1.0})
    rows.append({"market_id": "u", "fee_cat": "Politics", "liq": 5e4, "tick": 0.01, "rew_maxspread": 9.0, "rewarded": 0.0, "n_members": 1.0})
    d = pd.DataFrame(rows).set_index("market_id")
    d["bid"], d["ask"], d["spread"], d["t_row"], d["end_ts"], d["sports"], d["crypto7"] = 0.49, 0.51, 0.02, 0.0, np.nan, 0, "non_crypto"
    return d


def test_control_cell_rule_min20_fallback_uncovered_and_rows_regardless_of_cap():
    spec = lt.load_spec(sha=None)
    cells = lt.control_cells(_cell_frame(20, 5), spec)
    assert cells["cell"][("politics", "10k-100k", "0.01")][0] == 20  # the 20 rows have n_members 50: they still count (re-check fix 6)
    v, lev = lt.assign_control_band(np.array(["politics", "economy", "sports"]), np.array(["10k-100k"] * 3), np.array(["0.01"] * 3), cells, 20)
    assert v[0] == 4.0 and lev[0] == 2  # median of 3, 4, 5
    assert lev[1] == 1 and v[1] == cells["tt"][("10k-100k", "0.01")][1]  # economy has 5 < 20: the (tier, tick) fallback holds 25
    v2, lev2 = lt.assign_control_band(np.array(["economy"]), np.array([">=100k"]), np.array(["0.01"]), cells, 20)
    assert np.isnan(v2[0]) and lev2[0] == 0
    cells19 = lt.control_cells(_cell_frame(19, 0), spec)
    v3, lev3 = lt.assign_control_band(np.array(["politics"]), np.array(["10k-100k"]), np.array(["0.01"]), cells19, 20)
    assert np.isnan(v3[0]) and lev3[0] == 0


def test_fix_panels_first_unit_switch_exclusion_and_relpos_over_kept_units():
    U = pd.DataFrame({"market_id": ["a"] * 5 + ["b"] * 3, "slot": [1, 2, 3, 4, 5, 1, 2, 3], "rew": [1, 1, 0, 1, 0, 0, 1, 0],
                      "log_s": np.log([2.0, 4.0, 100.0, 8.0, 100.0, 3.0, 50.0, 6.0])})
    P, cnt = lt.fix_panels(U.sample(frac=1.0, random_state=1))
    assert cnt["panel_switched"] == 3 and cnt["panel_switched_reward"] == 2 and cnt["panel_switched_control"] == 1
    a = P[P["market_id"] == "a"].sort_values("slot")
    assert list(a["slot"]) == [1, 2, 4] and (a["panel"] == 1).all()
    assert np.isnan(a["relpos"].iloc[0])
    assert a["relpos"].iloc[1] == pytest.approx(np.log(4.0) - np.log(2.0))
    assert a["relpos"].iloc[2] == pytest.approx(np.log(8.0) - (np.log(2.0) + np.log(4.0)) / 2)  # the switched slot-3 unit never enters the mean
    bb = P[P["market_id"] == "b"].sort_values("slot")
    assert list(bb["slot"]) == [1, 3] and bb["relpos"].iloc[1] == pytest.approx(np.log(6.0) - np.log(3.0))


def test_ch213_design_matrix_has_interaction_controls_and_no_rew_regressor():
    assert "panel" not in lt.CONTROLS_213 and "rew" not in lt.CONTROLS_213
    for c in ("brk", "break_zliq", "break_tick", "break_zlogs", "break_relpos", "om", "break_om", *(f"sd{s}" for s in range(1, 12))):
        assert c in lt.CONTROLS_213
    p = lt.ch213_terms(pd.DataFrame({"brk": [1.0, 0.0], "panel": [1.0, 1.0], "log1p_liq": [1.0, 2.0], "log_s": [0.1, 0.2], "tick001": [0.0, 1.0], "relpos": [0.5, 0.1], "om": [1.0, 0.0]}))
    assert list(p["break_rew"]) == [1.0, 0.0] and list(p["break_om"]) == [1.0, 0.0] and list(p["break_relpos"]) == [0.5, 0.0]


# --- CH214 (design 3, re-check fix 2) ------------------------------------------------------------------------------------------------


def test_split_at_zero_change_never_centred():
    dD = np.array([-0.2, -0.01, 0.0, 0.01, 0.3])
    p, m = lt.split_innovation(dD, 0.1)
    assert np.allclose(p, [0, 0, 0, 0.1, 3.0]) and np.allclose(m, [-2.0, -0.1, 0, 0, 0])
    # a census centre below 0 cannot move a small departure into the arrival term (the centred zdD of a -0.01 change would be > 0)
    cen = -0.05
    assert (dD[1] - cen) / 0.1 > 0 and p[1] == 0.0
    assert np.isnan(lt.split_innovation(dD, float("nan"))[0]).all()


def test_band_sum_rule_and_per_side():
    s = lt.band_sum([1, 1], [2, 2], [10, 10], [20, 20], [1.5, 1.6], 1.5)
    assert list(s) == [3, 30]
    assert np.isnan(lt.band_sum([1], [2], [10], [20], [np.nan], 1.5)[0])


# --- CH212 route rule (design 4) -------------------------------------------------------------------------------------------------------


def test_route_rule_a_b_both_neither_and_nan():
    r = {"or_min": 1.5, "page_diff_min": 0.10, "dropped_share_min": 0.30}
    assert lt.route_rule({"or_vol_absent": 1.6, "or_ltp_absent": 1.0, "page_diff": 0.0, "dropped_share_of_transitions": 0.1}, r) == "A"
    assert lt.route_rule({"or_vol_absent": 1.0, "or_ltp_absent": 1.0, "page_diff": -0.12, "dropped_share_of_transitions": 0.1}, r) == "A"
    assert lt.route_rule({"or_vol_absent": 1.0, "or_ltp_absent": 1.0, "page_diff": 0.05, "dropped_share_of_transitions": 0.3}, r) == "B"
    assert lt.route_rule({"or_vol_absent": 2.0, "or_ltp_absent": 1.0, "page_diff": 0.05, "dropped_share_of_transitions": 0.9}, r) == "A"
    assert lt.route_rule({"or_vol_absent": 1.0, "or_ltp_absent": 1.4, "page_diff": 0.05, "dropped_share_of_transitions": 0.29}, r) == "dropped"
    assert lt.route_rule({"or_vol_absent": float("nan"), "or_ltp_absent": float("nan"), "page_diff": float("nan"), "dropped_share_of_transitions": float("nan")}, r) == "dropped"


def test_mantel_haenszel_and_page_difference():
    # one stratum: a=2 b=2 c=1 d=3 -> OR = (2*3/8) / (2*1/8) = 3
    y = [1, 1, 0, 0, 1, 0, 0, 0]
    x = [1, 1, 1, 1, 0, 0, 0, 0]
    assert lt.mh_odds_ratio(y, x, ["s"] * 8)["or"] == pytest.approx(3.0)
    assert lt.mh_odds_ratio([1, 0], [1, 1], ["s", "s"])["strata"] == 0  # no om = 0 rows: the stratum does not count
    pop = pd.DataFrame({"market_id": ["a", "a", "a", "b", "b", "c"], "om": [1.0, 0.0, 0.0, 1.0, 0.0, 1.0], "page_norm": [0.9, 0.5, 0.3, 0.2, 0.4, 0.0]})
    assert lt.page_diff(pop)["diff"] == pytest.approx(((0.9 - 0.4) + (0.2 - 0.4)) / 2) and lt.page_diff(pop)["markets"] == 2


# --- CH215 (design 5, re-check fix 1) --------------------------------------------------------------------------------------------------


def test_controls_assigned_in_decision_time_order_over_already_decided_ends():
    H = 3600.0
    ends = pd.DataFrame({"key": ["early_Te_decided_late", "late_Te_decided_early"], "condition_id": ["c1", "c2"], "T_e": [100 * H, 110 * H], "t_dec": [60 * H, 10 * H],
                         "event_id": ["e1", "e2"]})
    cands = {"early_Te_decided_late": ["m1", "m2", "m3", "m4"], "late_Te_decided_early": ["m1", "m2", "m9"]}
    out = lt.assign_controls(ends, cands, 3, 48 * H).set_index("key")
    assert out.loc["late_Te_decided_early", "controls"] == ["m1", "m2", "m9"]  # decided first: its controls are unchanged by the later decision
    assert out.loc["early_Te_decided_late", "controls"] == ["m3", "m4"]  # overlapping spans: m1, m2 already used
    far = ends.assign(T_e=[100 * H, 300 * H])
    out2 = lt.assign_controls(far, cands, 3, 48 * H).set_index("key")
    assert out2.loc["early_Te_decided_late", "controls"] == ["m1", "m2", "m3"]  # non-overlapping: reuse allowed (then clustered)
    none = lt.assign_controls(ends, {"early_Te_decided_late": ["m1"], "late_Te_decided_early": ["m1"]}, 3, 48 * H).set_index("key")
    assert none.loc["early_Te_decided_late", "n_controls"] == 0


def test_end_clusters_connected_components():
    e = pd.DataFrame({"event_id": ["A", "B", "C", "D"], "controls": [["m1"], ["m1", "m2"], ["m2"], ["m9"]]})
    cl = lt.end_clusters(e)
    assert cl.iloc[0] == cl.iloc[1] == cl.iloc[2] and cl.iloc[3] != cl.iloc[0]


# --- MDE arithmetic against the design text (planning inputs) ------------------------------------------------------------------------


def test_mde_formulas_reproduce_the_design_planning_values():
    a = {"t_sum": 3.47, "day_factor": 1.5}
    # CH213 (2): low panel after R1 retention: n_rb 5,998, n_rn 593,762, n_cb = n_rb, n_cn = 2 n_rn, SD 2c, DE 31, VIF 2 -> 1.50c
    assert lt.mde_ch213_declared(5998, 593762, 5998, 2 * 593762, 0.02, 31, a, 2.0) * 100 == pytest.approx(1.50, abs=0.005)
    assert lt.mde_ch213_declared(30228, 977369, 30228, 2 * 977369, 0.02, 31, a, 2.0) * 100 == pytest.approx(0.67, abs=0.005)
    # CH213 F-MDE at r 0.1: 2.24c
    assert lt.f_mde_gate(1.50, 0.1, 0.0)["f_mde_c"] == pytest.approx(2.236, abs=0.01)
    # CH214 (3): n_eff 295,732, DE 31, VIF 1.918, SD(zdD+) 0.58382, gap 2.2 -> 0.56c
    per_sd = b.mde_slope_declared(295732, 0.02, 31, a, 1.918)
    assert per_sd / 0.58382 * 2.2 * 100 == pytest.approx(0.56, abs=0.005)
    # CH212 route A (4): n1 35,322, n2 155,200, SD 3c, DE 31, VIF 1.3 -> 0.58c
    assert b.mde_class(35322, 155200, 0.03, 31, a, 1.3) * 100 == pytest.approx(0.584, abs=0.002)
    # CH215 (5): 3.47 x 2c x sqrt(2 / 170) x sqrt(3) x 1.5 x sqrt(1.3) = 2.23c
    assert 3.47 * 2 * math.sqrt(2 / 170) * math.sqrt(3) * 1.5 * math.sqrt(1.3) == pytest.approx(2.23, abs=0.005)
    assert lt.f_mde_gate(float("inf"), 0.1, 0.0)["f_mde_c"] == float("inf") and lt.f_mde_gate(0.5, float("nan"), 0.0)["f_mde_c"] == float("inf")


def test_every_section7_threshold_is_in_the_spec():
    g = lt.load_spec(sha=None)["census_gates"]
    assert g["mde_common"]["t_sum"] == 3.47 and g["mde_common"]["mde_max"] == 0.01 and g["mde_common"]["f_mde_max"] == 0.01
    assert g["mde_common"]["ch212_floor_A"] == 0.005 and g["mde_common"]["ch212_floor_B"] == 0.01
    c = g["CC9_CH213"]
    assert (c["finite_status_min"], c["units_projected_min"], c["control_band_coverage_min"], c["breaks_projected_min"], c["cap_share_min"], c["venue_clock_max"], c["vif_w_max"], c["block_share_min"], c["f_arm_min_share"], c["de_floor"]) == (0.95, 504000, 0.70, 17640, 0.40, 0.50, 3.0, 0.5, 0.5, 5.0)
    c = g["CS9_CH214"]
    assert (c["coverage_min"], c["quiet_share_min"], c["band_unchanged_min"], c["units_projected_min"], c["resid_iqr_min"], c["resid_iqr_markets_min"], c["vif_w_max"], c["r_gate_max"], c["pair_min_days"]) == (0.70, 0.50, 0.80, 252000, 0.05, 30, 2.0, 0.3, 5.0)
    c = g["CC9_CH212"]
    assert (c["switching_per_day_min"], c["routeA_omitted_projected_min"], c["routeB_dropped_projected_min"], c["vif_w_max"]) == (1500, 60480, 15120, 2.0)
    c = g["CR9_CH215"]
    assert (c["ends_projected_min"], c["clusters_projected_min"], c["control_share_min"], c["one_day_share_max"], c["end_moved_share_max"], c["de_floor"]) == (630, 100, 0.70, 0.30, 0.20, 3.0)
    ci = lt.load_spec(sha=None)["census_inputs"]
    assert ci["span"]["start_utc"] == "2026-11-02T00:00:00Z" and ci["span"]["end_utc"] == "2026-11-12T00:00:00Z" and ci["feed_completeness_min"] == 0.90
    assert ci["min_covered_days"] == {"CC9_CH213": 7.0, "CC9_CH212": 7.0, "CS9_CH214": 7.0, "CS9_F_pairs": 5.0, "CR9_CH215": 7.0} and ci["band_unit_check_cents"] == [0.5, 20]


def test_band_unit_check():
    spec = lt.load_spec(sha=None)
    assert lt.band_unit_check([3.5, 2.0, 4.5], spec)["ok"] and not lt.band_unit_check([0.035, 0.02], spec)["ok"] and not lt.band_unit_check([], spec)["ok"]


# --- synthetic host tree ---------------------------------------------------------------------------------------------------------------


def _spread(m: int, k: int) -> float:
    """Gamma spread: 0.02 normally, 0.04 (= 2v for v = 2c) every 5th slot on reward / control markets, giving strict breaks."""
    return 0.04 if (m % 4 in (0, 2) and (k + m) % 5 == 0) else 0.02


def _clob9(m: int, k: int) -> str | None:
    if m % 4 == 0:
        return LISTED
    if m % 4 == 1:
        return LISTED if k % 2 == 0 else None  # the field blinks: omitted at odd slots (carry lag 1)
    return None if m % 4 == 2 else "[]"


def write_capture(root: Path, k: int, wild: bool = False) -> str:
    start = _slot_dt(k)
    cid = start.strftime("%Y%m%dT%H%M%SZ") + f"_{k:08x}"
    d = root / cid
    d.mkdir(parents=True)
    rows, exts = [], []
    for m in range(N_MKT):
        mid = 0.40 + 0.002 * ((k + m) % 7)
        sp = _spread(m, k)
        cat = "Crypto" if m in (44, 45) else ("Sports" if m in (46, 47) else "Politics")
        rows.append({"received_utc": _iso(start + timedelta(seconds=5 + (m % 5))), "market_id": str(100 + m), "condition_id": f"0xc{m}", "event_id": str(10 + m // 3), "closed": "False",
                     "active": "True", "binary": 1, "best_bid": round(mid - sp / 2, 4) if not wild else 0.01, "best_ask": round(mid + sp / 2, 4) if not wild else 0.99, "spread": sp,
                     "last_trade_price": mid if m % 5 else np.nan, "chg_1h": 0.0, "chg_1d": 0.01, "chg_1w": 0.0, "liquidity": 5e4, "volume24hr": (1000.0 + 20.0 * k) if m % 3 else np.nan,
                     "end_date": (G0 + timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%SZ"), "clob_token_id_0": f"tok{m}", "neg_risk": "False"})
        exts.append({"market_id": str(100 + m), "fee_type": cat.lower() + "_fees", "fee_category": cat, "fees_enabled": "1", "fee_schedule": "", "order_price_min_tick_size": "0.01",
                     "created_at": _iso(G0 - timedelta(days=30)), "series_slugs": "", "rewards_min_size": "20", "rewards_max_spread": "2", "clob_rewards": _clob9(m, k),
                     "page_index": str(m // 10), "received_utc": _iso(start + timedelta(seconds=3 + m)), "volume_num": str(5000.0 + 10.0 * k + m), "competitive": "0.5" if m % 2 else ""})
    pd.DataFrame(rows).to_csv(d / "rows.csv.gz", index=False, compression="gzip")
    pd.DataFrame(exts).to_csv(d / "rows_ext.csv.gz", index=False, compression="gzip")
    (d / "manifest.json").write_text(json.dumps({"capture_id": cid, "state": "complete", "started_utc": _iso(start)}))
    return cid


def write_sweep(root: Path, cid: str, k: int, wild: bool = False) -> str:
    start = _slot_dt(k) + timedelta(minutes=6)
    name = start.strftime("%Y%m%dT%H%M%SZ") + f"_s{k:07x}"
    d = root / name
    d.mkdir(parents=True)
    rows = []
    for m in range(N_MKT):
        rng = np.random.default_rng(1000 * k + m)
        bs, as_ = 60.0 + 20 * rng.random(), 40.0 + 20 * rng.random()
        row = {"token_id": f"tok{m}", "market_id": str(100 + m), "batch_receipt_utc": _iso(start + timedelta(seconds=m)), "best_bid": 0.40, "best_ask": 0.41, "state": "two_sided",
               "bid_size_1": bs, "ask_size_1": as_, "depth_bid_1c": bs + 10 * rng.random(), "depth_ask_1c": as_ + 10 * rng.random(), "depth_bid_5c": bs + 100 + 80 * rng.random(),
               "depth_ask_5c": as_ + 100 + 80 * rng.random(), "min_order_size": 5.0, "n_bid_levels": 7, "n_ask_levels": 6, "tick_size": 0.01}
        if wild:  # every column a lag pass may NOT expose is wild; the four depths keep their true values
            row.update({"best_bid": 0.01, "best_ask": 0.99, "state": "one_sided", "bid_size_1": 9e9, "ask_size_1": -1.0, "min_order_size": 9e9, "batch_receipt_utc": "2030-01-01T00:00:00.000000Z"})
        rows.append(row)
    pd.DataFrame(rows).to_csv(d / "rows.csv.gz", index=False, compression="gzip")
    (d / "manifest.json").write_text(json.dumps({"state": "complete", "series_index": 0, "snapshot_id": cid}))
    return name


def write_feed(root: Path, k: int) -> str:
    start = _slot_dt(k) + timedelta(minutes=4)
    name = start.strftime("%Y%m%dT%H%M%SZ") + f"_f{k:06x}"
    recs = []
    for m in range(N_MKT):
        if m % 4 in (0, 1) and not (m == 1 and k >= 25):  # market 101 dropped by the CLOB from slot 25
            end = "2026-12-31" if m % 8 else _iso(_slot_dt(20 + (m % 16)) + timedelta(hours=5))
            recs.append({"feed": "native", "condition_id": f"0xc{m}", "rewards_max_spread": 2, "rewards_min_size": 20, "rewards_config": [{"rate_per_day": 10, "start_date": "2026-01-01", "end_date": end}]})
    _feed_dir(root, name, recs, start=start)
    return name


def build_host(tmp: Path, wild_caps: set[int] | None = None, wild_sweeps: set[int] | None = None) -> dict:
    snap, swp, feed = tmp / "host" / "snapshots", tmp / "host" / "book_sweeps", tmp / "host" / "reward_params"
    for p in (snap, swp, feed):
        p.mkdir(parents=True)
    cids = {k: write_capture(snap, k, wild=bool(wild_caps and k in wild_caps)) for k in range(0, SPAN[1] + 5)}
    sws = {k: write_sweep(swp, cids[k], k, wild=bool(wild_sweeps and k in wild_sweeps)) for k in range(SPAN[0] - 4, SPAN[1] + 5)}
    feeds = {k: write_feed(feed, k) for k in range(SPAN[0] - 14, SPAN[1] + 2)}
    return {"snap": snap, "swp": swp, "feed": feed, "cids": cids, "sws": sws, "feeds": feeds}


_BASE_SPEC = lt.load_spec(sha=None)


def make_spec() -> dict:
    spec = copy.deepcopy(_BASE_SPEC)
    ci = spec["census_inputs"]
    ci["span"] = {"start_utc": _iso(_slot_dt(SPAN[0]) - timedelta(minutes=31)), "end_utc": _iso(_slot_dt(SPAN[1]) + timedelta(minutes=89)), "first_slot_utc": _iso(_slot_dt(SPAN[0])),
                  "last_slot_utc": _iso(_slot_dt(SPAN[1]))}
    ci["refuse_at_or_after_utc"] = _iso(_slot_dt(SPAN[1] + 2) + timedelta(minutes=89))
    ci["min_covered_days"] = {k_: 0.5 for k_ in ci["min_covered_days"]}
    ci["expected_origins"] = {"CC9": SPAN[1] - SPAN[0] + 1, "CS9": SPAN[1] - SPAN[0] + 1}
    spec["tests"]["CH213"]["cell_min_units"] = 3
    spec["tests"]["CH215"].update({"knowledge_h": 6, "market_end_margin_h": 6, "control_exclusion_h": 12, "span_h": 6})  # a 2-day synthetic span
    return spec


@pytest.fixture()
def world(tmp_path, monkeypatch):
    design = tmp_path / "LIVE_TESTS_9.md"
    design.write_text("frozen design text")
    monkeypatch.setattr(lt, "DESIGN_PATH", design)
    monkeypatch.setattr(lt, "DESIGN_TEXT_SHA256", hashlib.sha256(design.read_bytes()).hexdigest())
    host = build_host(tmp_path)
    return {"tmp": tmp_path, "host": host, "spec": make_spec(), "design": design}


def do_seal(w, host=None, **kw):
    h = host or w["host"]
    return lt.seal_inputs(snapshot_root=[h["snap"]], sweep_root=[h["swp"]], feed_root=[h["feed"]], work=w["tmp"] / f"w_seal{len(list(w['tmp'].glob('w_seal*')))}", spec=w["spec"], **kw)


def write_seal(w, host=None, name="seal.json") -> Path:
    s = do_seal(w, host)
    assert "error" not in s, s
    p = w["tmp"] / name
    p.write_text(json.dumps(s, sort_keys=True, default=lt._json))
    return p


# --- the seal and its refusals -----------------------------------------------------------------------------------------------------------


def test_seal_windows_slots_feed_and_design_hash(world):
    s = do_seal(world)
    assert "error" not in s, s
    assert s["design_text_sha256"] == lt.DESIGN_TEXT_SHA256 and s["spec_blocks_sha256"] == lt.spec_blocks_sha(world["spec"])
    assert s["needs"]["captures"] == (SPAN[1] + 2) - (SPAN[0] - 12) + 1 and s["needs"]["sweeps"] == (SPAN[1] + 2) - (SPAN[0] - 2) + 1
    assert all(v["usable"] for v in s["feed"].values()) and s["needs"]["feed_captures"] > 0
    k = SPAN[0]
    assert s["slots"][world["host"]["cids"][k]] == lt.iso(b.slot_time(k, world["spec"]))
    assert world["host"]["cids"][SPAN[0] - 13] not in s["slots"]  # outside the capture window


def test_seal_refuses_other_design_text_and_conflicting_roots(world, monkeypatch):
    monkeypatch.setattr(lt, "DESIGN_TEXT_SHA256", "0" * 64)
    assert "differs from the text-frozen" in do_seal(world)["error"]
    monkeypatch.setattr(lt, "DESIGN_TEXT_SHA256", hashlib.sha256(world["design"].read_bytes()).hexdigest())
    other = world["tmp"] / "restore" / "snapshots"
    cid = world["host"]["cids"][SPAN[0]]
    (other / cid).mkdir(parents=True)
    for fn in ("rows.csv.gz", "manifest.json"):
        (other / cid / fn).write_bytes((world["host"]["snap"] / cid / fn).read_bytes())
    (other / cid / "rows_ext.csv.gz").write_bytes(b"different bytes")
    s = lt.seal_inputs(snapshot_root=[world["host"]["snap"], other], sweep_root=[world["host"]["swp"]], feed_root=[world["host"]["feed"]], work=world["tmp"] / "wx", spec=world["spec"])
    assert "two roots with different bytes" in s["error"]


def test_census_refusals(world):
    seal = write_seal(world)
    h = world["host"]
    kw = {"seal": seal, "snapshot_root": [h["snap"]], "feed_root": [h["feed"]], "spec": world["spec"]}
    work = world["tmp"] / "stale"
    work.mkdir()
    (work / "x").write_text("stale")
    assert "not empty" in lt.census_captures(work=work, **kw)["error"]
    spec2 = copy.deepcopy(world["spec"])
    spec2["census_gates"]["CC9_CH213"]["vif_w_max"] = 9.0
    assert "census blocks differ" in lt.census_captures(**{**kw, "spec": spec2}, work=world["tmp"] / "w1")["error"]
    cid = h["cids"][SPAN[0] + 3]
    p = h["snap"] / cid / "rows_ext.csv.gz"
    orig = p.read_bytes()
    p.write_bytes(orig + b"\n")
    r = lt.census_captures(work=world["tmp"] / "w2", **kw)
    assert "input identity" in r["error"] and any(x.get("error") == "sha256 mismatch" for x in r["bad"])
    p.write_bytes(orig)
    fd = h["feed"] / h["feeds"][SPAN[0] + 2]
    (fd / "rows.jsonl.gz").rename(fd / "gone.gz")
    r = lt.census_feed(work=world["tmp"] / "w3", **kw)
    assert "input identity" in r["error"]
    (fd / "gone.gz").rename(fd / "rows.jsonl.gz")
    sd = json.loads(seal.read_text())
    sd["design_text_sha256"] = "1" * 64
    s2 = world["tmp"] / "seal2.json"
    s2.write_text(json.dumps(sd))
    assert "different LIVE_TESTS_9.md" in lt.census_captures(**{**kw, "seal": s2}, work=world["tmp"] / "w4")["error"]
    sd = json.loads(seal.read_text())
    sd["slots"][h["cids"][SPAN[0]]] = "2027-01-01T00:31:00.000000Z"
    s3 = world["tmp"] / "seal3.json"
    s3.write_text(json.dumps(sd))
    assert "sealed bound" in lt.census_captures(**{**kw, "seal": s3}, work=world["tmp"] / "w5")["error"]
    spec3 = copy.deepcopy(world["spec"])
    spec3["reward_null_rule"] = "null_as_unrewarded"
    assert "error" in lt.census_captures(**{**kw, "spec": spec3}, work=world["tmp"] / "w6")
    import shutil
    shutil.rmtree(h["snap"] / h["cids"][SPAN[0] + 5])
    assert "input identity" in lt.census_captures(work=world["tmp"] / "w7", **kw)["error"]


def test_censuses_end_to_end_counts_only(world):
    seal = write_seal(world)
    h = world["host"]
    cc = lt.census_captures(seal=seal, snapshot_root=[h["snap"]], feed_root=[h["feed"]], work=world["tmp"] / "wc", spec=world["spec"])
    assert "error" not in cc, cc
    assert cc["covered_origins"]["CC9"] == SPAN[1] - SPAN[0] + 1 and cc["crypto_classifier_shown_to_work"]
    c13 = cc["CH213"]
    assert c13["units_reward_panel"] > 0 and c13["units_control_panel"] > 0 and c13["projected_reward_breaks_21d"] > 0
    assert "gate_CH213" in c13 and c13["gate_CH213"]["pass"] is False  # a 48-market world cannot reach 504,000 units
    assert c13["band_unit_check"]["ok"] and c13["band_unit_check"]["median_v_cents"] == 2.0
    c12 = cc["CH212"]
    assert c12["transitions_listed_to_null"] > 0 and c12["units_routeA"] > 0 and c12["route"] in ("A", "B", "dropped")
    assert c12["feed_completeness"]["ok"] and c12["switching_markets_mean_per_day"] > 0
    assert c12["feed_end_reasons"].get("feed_end_soon", 0) > 0  # the m % 8 == 0 programmes end inside the span
    e = cc["feed_end_kinds_of_positive_configs"]
    assert e["positive_configs"] > 0 and e["feed_captures_read"] > 0 and e["listed_markets"] >= e["feed_captures_read"]
    assert e["end_date_only"] + e["end_sentinel"] <= e["positive_configs"]
    assert e["date_only_share"] == e["end_date_only"] / e["positive_configs"] and e["sentinel_share"] == e["end_sentinel"] / e["positive_configs"]
    rf = cc["reward_field"]
    assert rf["null_taxonomy"].get("unset", 0) > 0 and rf["carry_counts"].get("rewards_null_carried_lag1", 0) > 0
    assert rf["two_ledger_map"]["listed_rewarded"] > 0 and rf["two_ledger_map"]["ghost"] > 0  # market 101 is dropped by the CLOB from slot 25
    assert rf["omitted_slots_per_market_day"]["ge3"] > 0 and rf["two_ledger_map"]["band_mismatch"] == 0
    cs = lt.census_sweeps(seal=seal, snapshot_root=[h["snap"]], sweep_root=[h["swp"]], feed_root=[h["feed"]], work=world["tmp"] / "ws", spec=world["spec"])
    assert "error" not in cs, cs
    c14 = cs["CH214"]
    assert 0.0 <= c14["dD"]["share_zdD_positive"] <= 1.0 and 0.0 <= c14["dD"]["share_positive"] <= 1.0
    assert c14["projected_units_21d"] > 0 and np.isfinite(c14["dD"]["scale"]) and c14["census_fixed"]["p_vm"] == 0.5 and c14["gate_CH214"]["pass"] is False
    cr = lt.census_feed(seal=seal, snapshot_root=[h["snap"]], feed_root=[h["feed"]], work=world["tmp"] / "wf", spec=world["spec"])
    assert "error" not in cr, cr
    assert cr["counts"]["ends_in_window_listed_ahead"] > 0 and cr["CH215"]["entered"] is False
    c15 = cr["CH215"]
    assert c15["qualifying_ends"] > 0 and c15["control_share_ge1"] > 0 and np.isfinite(c15["mde"]["mde_c"]) and c15["end_moved_share"] == 0.0


def test_causality_later_slots_never_reach_frozen_units(world, tmp_path):
    """CC9 reads no sweep: wild sweeps leave it byte-identical. CS9's lag passes (after the span) with wild prices / sizes / receipts and true
    depths leave every CS9 output identical: only the four depths pass the loader."""
    seal = write_seal(world)
    h = world["host"]
    cs1 = lt.census_sweeps(seal=seal, snapshot_root=[h["snap"]], sweep_root=[h["swp"]], feed_root=[h["feed"]], work=world["tmp"] / "a1", spec=world["spec"])
    cc1 = lt.census_captures(seal=seal, snapshot_root=[h["snap"]], feed_root=[h["feed"]], work=world["tmp"] / "a2", spec=world["spec"])
    w2 = {**world, "tmp": tmp_path / "second"}
    (tmp_path / "second").mkdir()
    h2 = build_host(tmp_path / "second", wild_sweeps={SPAN[1] + 1, SPAN[1] + 2, SPAN[1] + 3, SPAN[1] + 4})
    seal2 = write_seal(w2, h2)
    cs2 = lt.census_sweeps(seal=seal2, snapshot_root=[h2["snap"]], sweep_root=[h2["swp"]], feed_root=[h2["feed"]], work=tmp_path / "second" / "b1", spec=world["spec"])
    cc2 = lt.census_captures(seal=seal2, snapshot_root=[h2["snap"]], feed_root=[h2["feed"]], work=tmp_path / "second" / "b2", spec=world["spec"])
    dump = lambda d: json.dumps(d, sort_keys=True, default=lt._json)  # noqa: E731
    for k_ in ("files_checked",):
        cs1.pop(k_), cs2.pop(k_), cc1.pop(k_), cc2.pop(k_)
    assert dump(cs1["CH214"]) == dump(cs2["CH214"])
    assert dump(cc1["CH213"]) == dump(cc2["CH213"]) and dump(cc1["CH212"]) == dump(cc2["CH212"])


def test_bandbreak_units_read_nothing_after_k(world):
    """The unit builder takes the carried frames of k - 1 and k only; a wild capture k + 1 cannot be passed to it, and the CH213 twin path returns a
    flag only."""
    import inspect
    sig = inspect.signature(lt.bandbreak_units)
    assert list(sig.parameters)[:2] == ["ser_k", "ser_p"]
    h = world["host"]
    vp = pd.Series([0.02, 0.02], index=["100", "102"])
    fl = lt.lag_break_flag(h["snap"] / h["cids"][SPAN[0]], h["snap"] / h["cids"][SPAN[0] + 1], vp)
    assert fl.name == "break_twin" and set(np.unique(fl.dropna())) <= {0.0, 1.0} and len(fl) == 2


def test_lag_loaders_read_only_declared_columns(world, monkeypatch):
    h = world["host"]
    seen = []
    real = pd.read_csv

    def spy(path, *a, **kw):
        uc = kw.get("usecols")
        cols = list(real(path, nrows=0).columns)
        seen.append(sorted(c for c in cols if (uc(c) if callable(uc) else c in (uc or cols))))
        return real(path, *a, **kw)

    monkeypatch.setattr(pd, "read_csv", spy)
    k = SPAN[0] + 1
    out = lt.lag_band_sums(h["swp"] / h["sws"][k], h["snap"] / h["cids"][k])
    assert list(out.columns) == list(lt.LAG_SWEEP_COLUMNS)
    allowed = set(lt.LAG_SWEEP_COLUMNS) | set(lt.LAG_SWEEP_KEYS) | set(lt.LAG_CAPTURE_KEY_COLUMNS)
    assert all(set(s) <= allowed for s in seen), seen
    seen.clear()
    lt.lag_break_flag(h["snap"] / h["cids"][k], h["snap"] / h["cids"][k + 1], pd.Series([0.02], index=["100"]))
    assert all(set(s) <= set(lt.LAG_CAPTURE_COLUMNS) for s in seen), seen


def test_ops_stats_reads_no_price_column(tmp_path):
    root = tmp_path / "live_tests9"
    (root / "bandbreak" / "frozen").mkdir(parents=True)
    pd.DataFrame({"role": ["prospective_confirmation"], "panel": [1], "sports": [0], "crypto": [0], "s_k_c": [9.9]}).to_csv(root / "bandbreak" / "frozen" / "x.csv.gz", index=False, compression="gzip")
    out = lt.ops_stats(root)
    assert out["line_counts"]["bandbreak:panel:1"] == 1 and not any("s_k_c" in k for k in out["line_counts"])
    with pytest.raises(ValueError):
        lt._read_ops(root / "bandbreak" / "frozen" / "x.csv.gz", ["s_k_c"])


def test_header_precheck_reads_names_only(world):
    h = world["host"]
    k = SPAN[0]
    r = lt.header_precheck(capture_dir=h["snap"] / h["cids"][k], sweep_dir=h["swp"] / h["sws"][k], feed_dir=h["feed"] / h["feeds"][k], spec=world["spec"])
    assert r["rows_missing"] == [] and r["sidecar_missing"] == [] and r["sweep_missing"] == [] and r["feed_config_missing"] == []
    assert r["feed_missing"] == [] and r["ok"]


def test_code_hashes_and_spec_pin_rules(tmp_path):
    h = lt.code_hashes()
    assert h["live_tests9.py"] and h["live_tests9_base.py"] and h["live_tests9_analysis.py"] is None
    p = tmp_path / "spec.json"
    p.write_text(lt.SPEC_PATH.read_text())
    with pytest.raises(RuntimeError):
        lt.load_spec(p, sha="0" * 64)
    d = json.loads(p.read_text())
    d["census_gates"]["CC9_CH213"]["vif_w_max"] = float("nan")
    p.write_text(json.dumps(d))
    with pytest.raises(RuntimeError, match="NaN"):
        lt.load_spec(p, sha=lt.sha256_file(p))


# --- the runner ------------------------------------------------------------------------------------------------------------------------


def load_runner():
    spec = importlib.util.spec_from_file_location("run_lt9", HERE.parents[1] / "scripts" / "run_live_tests9.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_runner_refusals(tmp_path, monkeypatch, capsys):
    r = load_runner()
    for cmd in ("run", "backfill-series", "size-check", "analyze"):
        assert r.main([cmd]) == 2
    out = tmp_path / "o.json"
    out.write_text("{}")
    assert r.main(["ops-stats", "--out", str(out)]) == 1
    seal = tmp_path / "seal.json"
    seal.write_text("{}")
    assert r.main(["census-captures", "--seal", str(seal), "--work", str(tmp_path / "w")]) == 2  # not tracked by git
    monkeypatch.setattr(r, "_now", lambda: lt.epoch("2026-11-17T11:59:00Z"))
    assert r.main(["census-sweeps", "--seal", str(seal), "--work", str(tmp_path / "w")]) == 2  # before the CS9 not-before date
    monkeypatch.setattr(r, "_cap", lambda gb: True)
    assert r.main(["census-feed", "--seal", str(seal), "--work", str(tmp_path / "w"), "--data-dumps-cap-gb", "1"]) == lt.TEMPFAIL


# --- gates at their thresholds (constructed populations; counts only) ---------------------------------------------------------------


def test_cap_applies_before_the_panel_and_relpos():
    A = pd.DataFrame({"market_id": ["a", "a", "a"], "slot": [1, 2, 3], "rew": [0, 1, 1], "n_members": [20.0, 3.0, 3.0], "log_s": np.log([9.0, 2.0, 4.0])})
    U, cnt = lt.cap_then_panel(A, 10)
    assert list(U["slot"]) == [2, 3] and (U["panel"] == 1).all() and cnt["panel_switched"] == 0 and cnt["ladder_arm_candidates"] == 1
    assert U["relpos"].iloc[1] == pytest.approx(np.log(4.0) - np.log(2.0))  # the ladder origin never enters the mean
    assert cnt["cap_share_reward"] == 1.0


def _q15(n: int, days: int, moved: float = 0.0, ctl: int = 3) -> pd.DataFrame:
    rows = []
    for i in range(n):
        rows.append({"key": f"k{i}", "condition_id": f"c{i}", "T_e": 1e9 + i, "t_dec": 1e9, "event_id": f"e{i}", "cluster": f"e{i}", "n_controls": ctl if i % 10 else 0,
                     "controls": [], "end_moved": 1.0 if i < moved * n else 0.0, "day": f"2026-11-{4 + i % days:02d}"})
    return pd.DataFrame(rows)


def test_ch215_gates_and_entry():
    spec = lt.load_spec(sha=None)
    fc = {"ok": True, "share": 1.0, "slots": 96, "slots_with_usable_feed": 96}
    r = lt.census_ch215(_q15(4000, 8), {}, spec, fc, 8.0)
    assert r["gate_CH215"]["ends"] and r["gate_CH215"]["controls"] and r["gate_CH215"]["one_day"] and r["gate_CH215"]["end_moved"]
    assert r["entered"] is r["gate_CH215"]["pass"]
    r2 = lt.census_ch215(_q15(4000, 3), {}, spec, fc, 8.0)
    assert not r2["gate_CH215"]["one_day"] and not r2["entered"]  # one day holds 1/3 > 30%
    r3 = lt.census_ch215(_q15(4000, 8, moved=0.21), {}, spec, fc, 8.0)
    assert not r3["gate_CH215"]["end_moved"] and not r3["entered"]
    r4 = lt.census_ch215(_q15(200, 8), {}, spec, fc, 8.0)
    assert not r4["gate_CH215"]["ends"]  # 200 x 21 / 8 = 525 < 630
    r5 = lt.census_ch215(_q15(4000, 8), {}, spec, {**fc, "ok": False}, 8.0)
    assert not r5["entered"]
    r6 = lt.census_ch215(_q15(4000, 8), {}, spec, fc, 6.9)
    assert r6["gate_CH215"].get("values_nan") and not r6["entered"]  # below 7.0 covered days every gate is NaN and fails
    assert lt.census_ch215(pd.DataFrame(), {}, spec, fc, 8.0)["entered"] is False


def test_band_unit_failure_and_min_days_make_every_gate_nan():
    spec = lt.load_spec(sha=None)
    res = {"gate_CH213": {"a": True, "b": True, "pass": True}}
    out = lt._nan_gates(res, "gate_CH213", "band_unit")
    assert out["gate_CH213"]["pass"] is False and out["gate_CH213"]["values_nan"] and not out["gate_CH213"]["a"]
    out2 = b._gate_min_days({"gate_CH212": {"x": True, "pass": True}}, "gate_CH212", 6.9, spec["census_inputs"]["min_covered_days"]["CC9_CH212"])
    assert out2["gate_CH212"]["pass"] is False


def test_feed_completeness_share(tmp_path):
    spec = lt.load_spec(sha=None)
    k0 = 400
    for i in range(10):
        if i != 3:
            _feed_dir(tmp_path, f"f{i}", [{"condition_id": "x"}], start=datetime.fromtimestamp(b.slot_time(k0 + i, spec) + 240, UTC))
    _feed_dir(tmp_path, "fbad", [{"condition_id": "x"}], state="failed", start=datetime.fromtimestamp(b.slot_time(k0 + 3, spec) + 240, UTC))
    fc = lt.feed_completeness(lt.scan_feed([tmp_path]), list(range(k0, k0 + 10)), spec)
    assert fc["slots_with_usable_feed"] == 9 and fc["share"] == 0.9 and fc["ok"]
    fc2 = lt.feed_completeness(lt.scan_feed([tmp_path]), list(range(k0, k0 + 11)), spec)
    assert not fc2["ok"]


def test_route_is_dropped_when_the_feed_is_incomplete(world):
    seal = write_seal(world)
    h = world["host"]
    cc = lt.census_captures(seal=seal, snapshot_root=[h["snap"]], feed_root=[h["feed"]], work=world["tmp"] / "wc", spec=world["spec"])
    U = pd.DataFrame()  # the population is not needed to check the fail-closed route
    assert lt.census_ch212(U, {}, world["spec"], 1.0, {"ok": False}, {})["gate_CH212"]["pass"] is False
    assert cc["CH212"]["gate_CH212"]["feed_completeness"] is True
    tot = {"eligible_in_band": 10, "eligible_in_band_status_finite": 10}
    pop = pd.DataFrame({"market_id": ["a", "a", "b", "b"], "day": "d", "slot": [1, 2, 1, 2], "t_row": [1.0, 2.0, 1.0, 2.0], "event_id": ["e", "e", "f", "f"], "n_members": 1.0,
                        "om": [1.0, 0.0, 1.0, 0.0], "listed_prev": [1.0, 1.0, 1.0, 1.0], "clob_listed": [1.0, 1.0, 1.0, 1.0], "clob_dropped": [0.0, 0.0, 0.0, 0.0],
                        "feed_end_ok": 1.0, "feed_end_why": "", "vol_absent": [1.0, 0.0, 1.0, 0.0], "ltp_absent": 0.0, "page_norm": 0.5, "recv_off": 1.0, "skey": "s", "f_ok": 1.0})
    r = lt.census_ch212(pop, tot, world["spec"], 1.0, {"ok": False}, {"per_day": {"d": 5000}})
    assert r["route"] == "dropped" and r["gate_CH212"]["route"] is False and r["gate_CH212"]["feed_completeness"] is False


def test_causality_wild_captures_after_the_span(world, tmp_path):
    """Captures after the span with wild prices: CC9's frozen states (every CH213 quantity except the twin's F inputs) and all of CH212 (its twin is
    a status only) and CS9 (capture k gives its start only) are unchanged."""
    seal = write_seal(world)
    h = world["host"]
    cc1 = lt.census_captures(seal=seal, snapshot_root=[h["snap"]], feed_root=[h["feed"]], work=world["tmp"] / "a2", spec=world["spec"])
    cs1 = lt.census_sweeps(seal=seal, snapshot_root=[h["snap"]], sweep_root=[h["swp"]], feed_root=[h["feed"]], work=world["tmp"] / "a3", spec=world["spec"])
    (tmp_path / "second").mkdir()
    w2 = {**world, "tmp": tmp_path / "second"}
    h2 = build_host(tmp_path / "second", wild_caps={SPAN[1] + 1, SPAN[1] + 2, SPAN[1] + 3, SPAN[1] + 4})
    seal2 = write_seal(w2, h2)
    cc2 = lt.census_captures(seal=seal2, snapshot_root=[h2["snap"]], feed_root=[h2["feed"]], work=tmp_path / "second" / "b2", spec=world["spec"])
    cs2 = lt.census_sweeps(seal=seal2, snapshot_root=[h2["snap"]], sweep_root=[h2["swp"]], feed_root=[h2["feed"]], work=tmp_path / "second" / "b3", spec=world["spec"])
    dump = lambda d: json.dumps(d, sort_keys=True, default=lt._json)  # noqa: E731
    assert dump(cc1["CH212"]) == dump(cc2["CH212"]) and dump(cs1["CH214"]) == dump(cs2["CH214"])
    f_keys = {"F", "F_arm_share", "pairs", "gate_CH213", "broken_at_km1_given_km2_pooled"}
    assert dump({k: v for k, v in cc1["CH213"].items() if k not in f_keys}) == dump({k: v for k, v in cc2["CH213"].items() if k not in f_keys})


def test_feed_end_kinds_counted_once_after_cache_eviction(world, monkeypatch):
    """The feed-frame cache keeps 4 frames; a re-read after eviction must not be counted twice."""
    seal = write_seal(world)
    h = world["host"]
    calls: dict[str, int] = {}
    totals: dict[str, tuple[int, int, int, int]] = {}
    orig = lt.feed_frame

    def spy(feed_dir, spec):
        f = orig(feed_dir, spec)
        k = str(feed_dir)
        calls[k] = calls.get(k, 0) + 1
        totals[k] = (len(f), int(f["n_pos"].sum()), int(f["n_date_only"].sum()), int(f["n_sentinel"].sum()))
        return f

    monkeypatch.setattr(lt, "feed_frame", spy)
    monkeypatch.setattr(lt, "FEED_CACHE_FRAMES", 1)
    cc = lt.census_captures(seal=seal, snapshot_root=[h["snap"]], feed_root=[h["feed"]], work=world["tmp"] / "wev", spec=world["spec"])
    assert "error" not in cc, cc
    e = cc["feed_end_kinds_of_positive_configs"]
    assert any(n > 1 for n in calls.values()), "fixture must exercise eviction and re-read"
    assert e["feed_captures_read"] == len(totals)
    assert e["listed_markets"] == sum(t[0] for t in totals.values()) and e["positive_configs"] == sum(t[1] for t in totals.values())
    assert e["end_date_only"] == sum(t[2] for t in totals.values()) and e["end_sentinel"] == sum(t[3] for t in totals.values())


# --- census code check 2026-10-23 (reviews/LT9_CENSUS_CODE_CHECK_2026-10-23.md) -----------------------------------------------------------


def test_missing_sealed_sidecar_refuses_the_census(world):
    """Must-fix 1: a sealed rows_ext absent from every root makes every census refuse (the vendored capture_files skips a missing sidecar)."""
    seal = write_seal(world)
    h = world["host"]
    kw = {"seal": seal, "snapshot_root": [h["snap"]], "feed_root": [h["feed"]], "spec": world["spec"]}
    (h["snap"] / h["cids"][SPAN[0] + 3] / "rows_ext.csv.gz").unlink()
    r = lt.census_captures(work=world["tmp"] / "m1", **kw)
    assert "input identity" in r["error"] and any(x.get("error") == "sealed but absent locally" for x in r["bad"]) and "CH213" not in r
    assert "input identity" in lt.census_feed(work=world["tmp"] / "m2", **kw)["error"]
    assert "input identity" in lt.census_sweeps(work=world["tmp"] / "m3", sweep_root=[h["swp"]], **kw)["error"]


def test_decision_capture_is_the_last_with_last_receipt_strictly_before(world):
    """Must-fix 2: a capture in progress at the decision time is never CR9's decision capture."""
    assert lt.decision_slot([10, 11, 12], [100.0, 200.0, 300.0], 250.0) == 11  # capture 12 started before 250 but is still receiving rows
    assert lt.decision_slot([10, 11, 12], [100.0, 200.0, 300.0], 200.0) == 10  # strictly earlier
    assert lt.decision_slot([10, 11, 12], [100.0, 200.0, 300.0], 50.0) == -10**9
    h = world["host"]
    assert lt.capture_last_receipt(h["snap"] / h["cids"][SPAN[0]]) == lt.epoch(_iso(_slot_dt(SPAN[0]))) + 9.0
    # end to end: capture 2 (the first sealed capture) is still receiving rows when the first sealed feed capture finishes (slot 2 + 5 min)
    def decide(tmp: Path, late: bool):
        tmp.mkdir()
        host = build_host(tmp)
        if late:
            p = host["snap"] / host["cids"][2] / "rows.csv.gz"
            df = pd.read_csv(p, dtype=str)
            df.loc[0, "received_utc"] = _iso(_slot_dt(2) + timedelta(minutes=10))
            df.to_csv(p, index=False, compression="gzip")
        w = {**world, "tmp": tmp}
        seal = write_seal(w, host)
        return lt.census_feed(seal=seal, snapshot_root=[host["snap"]], feed_root=[host["feed"]], work=tmp / "wf", spec=world["spec"])
    base, late = decide(world["tmp"] / "d0", False), decide(world["tmp"] / "d1", True)
    assert "error" not in base and "error" not in late, (base, late)
    assert late["counts"]["no_decision_capture"] > base["counts"].get("no_decision_capture", 0)


def test_ch213_control_twin_uses_v_ctrl_of_capture_k_plus_5_cell(world):
    """Must-fix 3: a control unit's twin band is the (cat, tier, tick) median of capture k + 5, computed inside the loader (the flag only returns)."""
    h = world["host"]
    k = 20  # market 100: spread 2c at k + 4 = 24 and 4c at k + 5 = 25 (every 5th slot)
    ca, cb = h["snap"] / h["cids"][k + 4], h["snap"] / h["cids"][k + 5]
    grp = pd.DataFrame({"market_id": ["100"], "fee_cat": ["Politics"], "liq": [5e4], "tick": [0.01], "rew": [0.0], "v_c": [1.0]}, index=[7])
    key = (lt.cat_key(grp["fee_cat"])[0], lt.tier_of(grp["liq"])[0], lt.tick_key(grp["tick"])[0])
    cells5 = {"cell": {key: (25, 2.0)}, "tt": {}}
    fl = lt.lag_twin_flags(ca, cb, grp, cells5, world["spec"])
    assert list(fl.index) == [7] and fl.iloc[0] == 1.0  # 2 < 4 <= s_b: broken against k + 5's median v = 2c (k's own v_ctrl = 1c would give 0)
    assert lt.lag_twin_flags(ca, cb, grp, {"cell": {key: (25, 1.0)}, "tt": {}}, world["spec"]).iloc[0] == 0.0
    assert np.isnan(lt.lag_twin_flags(ca, cb, grp, None, world["spec"]).iloc[0])  # no k + 5 cell: NaN
    assert np.isnan(lt.lag_twin_flags(ca, cb, grp, {"cell": {key: (2, 2.0)}, "tt": {}}, world["spec"]).iloc[0])  # cell below the minimum, no fallback
    assert lt.lag_twin_flags(ca, cb, grp.assign(rew=1.0, v_c=2.0), None, world["spec"]).iloc[0] == 1.0  # a reward unit keeps its own v
    import inspect
    assert "mid" not in inspect.getsource(lt.lag_twin_flags).replace("midpoint", "")


def test_ch215_control_ties_break_by_condition_id():
    pool = pd.DataFrame({"market_id": ["m1", "m2", "m3"], "condition_id": ["0xc", "0xa", "0xb"], "loglq": [5.0, 5.0, 5.0]})
    assert lt.rank_control_candidates(pool, 5.0) == ["m2", "m3", "m1"]  # by condition_id, not market_id
    assert lt.rank_control_candidates(pool.assign(loglq=[5.0, 6.0, 4.5]), 5.0) == ["m1", "m3", "m2"]
    assert "condition_id" in json.loads(lt.SPEC_PATH.read_text())["tests"]["CH215"]["control_rule"]


def test_cr9_feed_completeness_covers_all_span_slots(world):
    assert len(lt._span_slots(_BASE_SPEC)) == 120
    seal = write_seal(world)
    h = world["host"]
    cr = lt.census_feed(seal=seal, snapshot_root=[h["snap"]], feed_root=[h["feed"]], work=world["tmp"] / "wf", spec=world["spec"])
    assert cr["feed_completeness"]["slots"] == len(lt._span_slots(world["spec"]))


def test_malformed_beats_open_beats_dated_and_mixed_cases_are_counted(tmp_path):
    spec = lt.load_spec(sha=None)
    recs = [{"feed": "native", "condition_id": "a", "rewards_config": [{"rate_per_day": 5, "end_date": "junk"}, {"rate_per_day": 5, "end_date": "2026-11-05"}]},
            {"feed": "native", "condition_id": "b", "rewards_config": [{"rate_per_day": 5, "end_date": "junk"}, {"rate_per_day": 5, "end_date": None}]},
            {"feed": "native", "condition_id": "c", "rewards_config": [{"rate_per_day": 5, "end_date": None}, {"rate_per_day": 5, "end_date": "2026-11-05"}]},
            {"feed": "native", "condition_id": "d", "rewards_config": [{"rate_per_day": 5, "end_date": "junk"}]}]
    f = lt.feed_frame(_feed_dir(tmp_path, "f1", recs), spec)
    assert f["end_kind"].to_dict() == {"a": "malformed", "b": "malformed", "c": "open", "d": "malformed"}
    assert f["mixed_malformed"].to_dict() == {"a": True, "b": True, "c": False, "d": False}
    ok, why = lt.feed_end_ok(pd.Series(["a", "c"]), f, 3, spec)
    assert np.isnan(ok[0]) and why[0] == "feed_end_malformed" and ok[1] == 1.0
    assert json.loads(lt.SPEC_PATH.read_text())["declared_before_seal"]["end_kind_precedence"]["rule"].startswith("malformed > open > dated")


def test_sentinel_year_is_read_as_written():
    assert lt.parse_end("2099-12-31T23:00:00-05:00")[2] == "ts"  # as written 2099; UTC is 2100-01-01T04:00Z
    assert lt.parse_end("2100-01-01T01:00:00+05:00")[2] == "sentinel"  # as written 2100 although UTC is 2099-12-31T20:00Z


def test_ghost_market_is_its_own_feed_end_category(tmp_path):
    spec = lt.load_spec(sha=None)
    f = lt.feed_frame(_feed_dir(tmp_path, "f1", [{"feed": "native", "condition_id": "listed_no_pos", "rewards_config": [{"rate_per_day": 0, "end_date": None}]}]), spec)
    ok, why = lt.feed_end_ok(pd.Series(["listed_no_pos", "ghost"]), f, 3, spec)
    assert list(why) == ["feed_no_positive_config", "feed_unlisted"] and np.isnan(ok).all()


def test_scan_feed_reads_only_the_named_manifests(tmp_path):
    _feed_dir(tmp_path, "fa", [{"condition_id": "x"}])
    _feed_dir(tmp_path, "fb", [{"condition_id": "x"}])
    (tmp_path / "fb" / "manifest.json").write_text("not json at all")
    assert set(lt.scan_feed([tmp_path], only={"fa"})) == {"fa"}
    assert set(lt.scan_feed([tmp_path], only={"fa", "missing"})) == {"fa"}
    assert set(lt.scan_feed([tmp_path])) == {"fa"}  # the unrestricted scan skips an unreadable manifest


def test_cr9_and_cc9_print_declared_denominators_and_descriptives(world):
    seal = write_seal(world)
    h = world["host"]
    kw = {"seal": seal, "snapshot_root": [h["snap"]], "feed_root": [h["feed"]], "spec": world["spec"]}
    cr = lt.census_feed(work=world["tmp"] / "wf", **kw)
    c = cr["counts"]
    assert cr["declared_before_seal"] and c["positive_configs"] > 0 and c["date_only_share"] == c["end_date_only"] / c["positive_configs"]
    assert c["sentinel_share"] == c["end_sentinel"] / c["positive_configs"] and "denominators differ" in c["end_kind_denominator"]
    assert 0.0 < c["share_listed_ge_48h_ahead"] <= 1.0 and c["ends_in_window_seen"] >= c["ends_in_window_listed_ahead"]
    sp = c["sponsored_shares_of_decisions"]
    assert abs(sp["sponsored_only"] + sp["native_and_sponsored"] + sp["native_only"] - 1.0) < 1e-9 and sp["native_only"] == 1.0  # the synthetic feed is all native
    assert c["moved_between_consecutive_feed_captures"]["pairs"] > 0 and c["moved_between_consecutive_feed_captures"]["share"] == 0.0
    assert all(np.isnan(v["units"]) and v["reason"] for v in c["overlaps_with_prior_populations"].values())
    cc = lt.census_captures(work=world["tmp"] / "wc", **kw)
    assert cc["declared_before_seal"] and "denominator" in cc["feed_end_kinds_of_positive_configs"] and "feed_end_shares_denominator" in cc["CH212"]
    assert "switching_gate_definition" in cc["CH212"] and "feed_unlisted" not in cc["CH212"]["feed_end_shares"]
    assert cc["overlaps_with_prior_populations"]["LT8_CH203"]["reason"] and "malformed_mixed_markets" in cc["feed_end_kinds_of_positive_configs"]


def test_census_captures_builds_cells5_from_capture_k_plus_5(world, monkeypatch):
    """Re-check item 3: census_captures hands lag_twin_flags the cell medians of capture k + 5 (not k), end to end. Changing capture k + 5's reward band
    changes the control units' twin flag of origin k and of no other origin."""
    seen: dict[int, tuple[dict, pd.Series]] = {}
    orig = lt.lag_twin_flags

    def spy(cap_a, cap_b, grp, cells_b, spec):
        fl = orig(cap_a, cap_b, grp, cells_b, spec)
        seen[int(grp["slot"].iloc[0])] = (cells_b, fl.set_axis(grp["market_id"].astype(str).to_numpy()), grp)
        return fl

    monkeypatch.setattr(lt, "lag_twin_flags", spy)

    def run(tmp: Path, band: str | None):
        tmp.mkdir()
        host = build_host(tmp)
        if band is not None:
            p = host["snap"] / host["cids"][KK + 5] / "rows_ext.csv.gz"
            ext = pd.read_csv(p, dtype=str, keep_default_na=False)
            ext["rewards_max_spread"] = band
            ext.to_csv(p, index=False, compression="gzip")
        w = {**world, "tmp": tmp}
        seal = write_seal(w, host)
        seen.clear()
        cc = lt.census_captures(seal=seal, snapshot_root=[host["snap"]], feed_root=[host["feed"]], work=tmp / "wc", spec=world["spec"])
        assert "error" not in cc, cc
        return dict(seen)

    KK = SPAN[0] + 2
    base, changed = run(world["tmp"] / "t0", None), run(world["tmp"] / "t1", "4")
    assert KK in base and KK in changed
    meds = lambda cells: sorted({v[1] for v in cells["cell"].values()})  # noqa: E731
    assert meds(base[KK][0]) == [2.0] and all(m_ > 2.0 for m_ in meds(changed[KK][0]))  # cell medians of capture KK + 5 reach the loader (carried rewarded rows keep their source's band, so 4 gives 3)
    ctrl = base[KK][2]["rew"].to_numpy(float) != 1.0
    assert ctrl.any()
    fb, fc_ = base[KK][1].to_numpy(float)[ctrl], changed[KK][1].to_numpy(float)[ctrl]
    assert not np.array_equal(fb, fc_, equal_nan=True) and (fb == 1.0).any() and (fc_[np.isfinite(fc_)] == 0.0).all()  # 2v = 4c breaks, 2v = 6c does not
    for k in base:  # other origins' cells come from their own k + 5 capture, which this edit did not touch
        if k != KK:
            assert meds(base[k][0]) == meds(changed[k][0]) == [2.0]


def _malform_feed(host: dict, cids: set[str]) -> None:
    for d in host["feed"].iterdir():
        p = d / "rows.jsonl.gz"
        with gzip.open(p, "rt") as fh:
            recs = [json.loads(x) for x in fh]
        for r in recs:
            if r["condition_id"] in cids:
                r["rewards_config"] = r["rewards_config"] + [{"rate_per_day": 5, "start_date": "2026-01-01", "end_date": "junk"}]
        with gzip.open(p, "wt") as fh:
            for r in recs:
                fh.write(json.dumps(r) + "\n")


def test_cr9_control_pool_excludes_malformed_markets_and_counts_them(world):
    """Re-check item 4 and item 1: markets whose feed end kind is malformed (unknown end) leave the control pool, counted with a denominator."""
    def run(tmp: Path, bad: set[str]):
        tmp.mkdir()
        host = build_host(tmp)
        _malform_feed(host, bad)
        w = {**world, "tmp": tmp}
        seal = write_seal(w, host)
        return lt.census_feed(seal=seal, snapshot_root=[host["snap"]], feed_root=[host["feed"]], work=tmp / "wf", spec=world["spec"])
    base = run(world["tmp"] / "m0", set())
    bad = run(world["tmp"] / "m1", {"0xc4", "0xc12", "0xc16"})
    for r in (base, bad):
        assert "error" not in r, r
    e0, e1 = base["counts"]["control_pool_malformed_excluded"], bad["counts"]["control_pool_malformed_excluded"]
    assert e0["candidates_excluded"] == 0 and e0["candidates_before_exclusion"] > 0 and e0["denominator"]
    assert e1["candidates_excluded"] > 0 and e1["candidates_excluded"] <= e1["candidates_before_exclusion"] and 0 < e1["share"] <= 1
    nr = base["counts"]["captures_no_readable_receipt"]
    assert nr["n"] == 0 and nr["of_captures"] > 0 and nr["share"] == 0.0 and nr["denominator"]


def test_cr9_counts_captures_without_a_readable_receipt(world):
    h = world["host"]
    p = h["snap"] / h["cids"][SPAN[0] + 1] / "rows.csv.gz"
    df = pd.read_csv(p, dtype=str)
    df["received_utc"] = ""
    df.to_csv(p, index=False, compression="gzip")
    seal = write_seal(world)
    cr = lt.census_feed(seal=seal, snapshot_root=[h["snap"]], feed_root=[h["feed"]], work=world["tmp"] / "wf", spec=world["spec"])
    nr = cr["counts"]["captures_no_readable_receipt"]
    assert nr["n"] == 1 and nr["share"] == 1 / nr["of_captures"]


def test_cs9_prior_population_overlaps_and_reasons(world):
    seal = write_seal(world)
    h = world["host"]
    kw = {"seal": seal, "snapshot_root": [h["snap"]], "feed_root": [h["feed"]], "spec": world["spec"]}
    cs = lt.census_sweeps(sweep_root=[h["swp"]], work=world["tmp"] / "ws", **kw)
    ov = cs["overlaps_with_prior_populations"]
    assert np.isnan(ov["LT8_CH203"]["units"]) and "capture k" in ov["LT8_CH203"]["reason"]
    o7 = ov["LT7_CH197"]
    assert o7["key"] == "(market, UTC day)" and o7["passes_12_31Z_in_span_with_sweep_read"] >= 1 and o7["units_ch197"] > 0 and o7["units"] >= 0
    assert "share_of_CH197" in o7 and "share_of_CH214" in o7
    cr = lt.census_feed(work=world["tmp"] / "wf", **kw)
    cc = lt.census_captures(work=world["tmp"] / "wc", **kw)
    for ovs in (cr["counts"]["overlaps_with_prior_populations"], cc["overlaps_with_prior_populations"]):
        assert all(np.isnan(v["units"]) and v["reason"] == "census reads no sweeps" for v in ovs.values())
    d = json.loads(lt.SPEC_PATH.read_text())["declared_before_seal"]
    assert "DECLARED DEVIATION" in d["prior_population_overlaps"]["rule"] and "section 7" in d["prior_population_overlaps"]["rule"]
    assert d["control_pool_malformed"] and d["captures_no_readable_receipt"]


def test_prior_population_specs_equal_the_prior_spec_files():
    ps = lt.load_spec(sha=None)["prior_population_specs"]
    s8 = json.loads((lt.SPEC_PATH.parent / "live_tests8_v1.json").read_text())
    s7 = json.loads((lt.SPEC_PATH.parent / "live_tests7_v1.json").read_text())
    assert ps["LT8_CH203"]["test"] == s8["tests"]["CH203"] and ps["LT8_CH203"]["ft_factor"] == s8["reward_rule"]["ft_factor"] and ps["LT8_CH203"]["member_cap_max"] == s8["member_cap"]["max_members"]
    assert ps["LT7_CH197"]["test"] == s7["tests"]["CH197"]
    assert "prior_population_specs" in lt.SPEC_HASHED_BLOCKS
    for name in ("quiet_units", "_sw_take", "_rewards", "effective_text", "rw_nocol_mask", "behind_touch", "patient_units"):
        assert name in b.VENDORED and b.VENDORED[name]["source"] in ("live_tests7.py", "live_tests8.py")
    assert b._Q_EPS == l8._Q_EPS and b._SW_COLS == l8._SW_COLS
