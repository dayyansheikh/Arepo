# ruff: noqa: E501
"""LT6 (LIVE_TESTS_6.md) code unit 1: spec and pins, the registration-date rule and V's E022 freeze condition, the pinned
crypto classifier, K's deterministic clip-train algorithm (every branch), V's state and depletion gates, D's deadline
classifier and parse rules, B's birth classes, the washout. Synthetic data only; no network; no price after an origin."""

from __future__ import annotations

import copy
import math
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import live_tests6 as lt

HERE = Path(lt.__file__).resolve().parent


def _spec() -> dict:
    return lt.load_spec(sha=None)


# --- spec and pins -------------------------------------------------------------------------------------------------------


def test_draft_spec_loads_with_null_placeholders():
    s = _spec()
    assert s["_pinned"] is False and lt.SPEC_SHA256 is None
    assert s["registered_utc"] is None and s["end_utc"] is None and s["analysis_not_before"] is None
    assert lt.REGISTERED_UTC is None and lt.END_UTC is None and lt.ANALYSIS_NOT_BEFORE is None
    assert s["k_tests"] is None and s["code_sha256"] is None
    assert s["proposed_dates_if_e022_unmoved"]["registered_utc"] == "2026-11-16T00:00:00Z"


def test_spec_constants_are_exactly_the_designs():
    s = _spec()
    assert s["seeds"] == {"V": 20261161, "K": 20261162, "D": 20261163, "B": 20261164, "V_gate": 20261261, "K_gate": 20261262,
                          "D_gate": 20261263, "B_gate": 20261264, "B_fake_birth": 20261364}
    sc = s["size_check"]
    assert sc["seed"] == 20261167 and sc["worlds"] == 2000 and sc["draws"] == 200
    assert sc["nonbinding"]["s12_label_correlated_with_level"]["seed"] == 2026116712
    assert [sc["nonbinding"][f"power_{t}"]["seed"] for t in ("d_0.5c", "d_1.0c", "b_0.5c", "b_1.0c")] == [2026116721, 2026116722, 2026116723, 2026116724]
    assert sorted(t for v in sc["scenarios"].values() for t in v) == ["B", "B", "D", "K", "K", "K", "K", "K", "V", "V", "V"]
    g = s["census_gates"]
    assert g["mde_common"]["t_sum"] == 3.388 and g["mde_common"]["de_floor"] == 3.0 and g["mde_common"]["day_factor"] == 1.5
    assert g["CV_V"]["units_projected_min"] == 42000 and g["CV_V"]["depletion_1c_asym_pp_max"] == 0.20 and g["CV_V"]["depletion_5c_toward_share_max"] == 0.50
    assert g["CK_K"]["qualifying_projected_min"] == 50400 and g["CK_K"]["clip_projected_min"] == 8400 and g["CK_K"]["clip_free_projected_min"] == 25200
    assert g["CD_D"]["later_units_projected_min"] == 3150 and g["CB_B"]["births_projected_min"] == 630 and g["CB_B"]["birth_units_projected_min"] == 3150
    assert s["census_inputs"]["min_covered_days"] == {"CV": 1.5, "CK": 1.5, "CD": 5, "CB": 5}
    assert s["k"]["clip_share_min"] == 0.25 and s["d"]["later_min_s"] == 3600 and s["b"]["guard_s"] == 5.0
    assert s["labels"]["material_b_c"] == 1.0 and s["gates"]["draws"] == 200 and s["gates"]["block_min_n"] == 16


def test_code_files_exist_and_hash_is_pin_line_independent(tmp_path):
    for n in lt.CODE_FILES:
        if n != "live_tests6_analysis.py":  # written in a later unit
            assert (HERE / n).exists(), n
    f = tmp_path / "m.py"
    f.write_text('A = 1\nSPEC_SHA256 = None\n')
    h1 = lt.code_sha256(f)
    f.write_text('A = 1\nSPEC_SHA256 = "abc"\n')
    assert lt.code_sha256(f) == h1
    f.write_text('A = 2\nSPEC_SHA256 = None\n')
    assert lt.code_sha256(f) != h1


def test_pinned_spec_refuses_hash_mismatch_and_null_placeholders(tmp_path):
    with pytest.raises(RuntimeError, match="sha256 mismatch"):
        lt.load_spec(sha="0" * 64)
    with pytest.raises(RuntimeError, match="placeholders"):
        lt.load_spec(sha=lt.sha256_file(lt.SPEC_PATH))


def test_unfilled_lists_required_and_per_test_values():
    s = _spec()
    miss = lt.unfilled(s)
    assert {"registered_utc", "end_utc", "analysis_not_before", "k_tests", "code_sha256", "e022.registered|e022.dropped", "labels.partially_seen_d"} <= set(miss)
    s2 = {**s, "registered_utc": "x", "end_utc": "x", "analysis_not_before": "x", "k_tests": ["V", "B"], "code_sha256": {"a": "b"},
          "e022": {**s["e022"], "dropped": True}, "labels": {**s["labels"], "partially_seen_d": False},
          "size_check": {**s["size_check"], "result_path": "docs/x.json", "result_sha256": "0" * 64}}
    miss = lt.unfilled(s2)
    assert "v.c_v" in miss and "b.fake_birth_terciles" in miss and "d.exclude_family" not in miss and "e022.registered|e022.dropped" not in miss
    s2["v"] = {**s["v"], "c_v": 0.1, "s_v": 0.3, "terciles": [0.0, 0.1], "tercile_gap": 2.2, "exclude_family": ""}
    s2["b"] = {**s["b"], "exclude_family": "", "perm_stratum": "day", "fake_birth_terciles": [0.1, 0.2]}
    assert lt.unfilled(s2) == []
    s2["v"]["c_v"] = float("nan")
    assert "v.c_v" in lt.unfilled(s2)
    s2["v"]["c_v"] = 0.1
    assert {"size_check.result_path", "size_check.result_sha256"} <= set(lt.unfilled({**s2, "size_check": s["size_check"]}))


def test_freeze_check_fixes_e022_end_utc_pin_commit_and_v_freeze_enforced():
    s = copy.deepcopy(_spec())
    s.update(k_tests=["V"], registered_utc="x", end_utc="x", analysis_not_before="x", code_sha256={"a": "b"}, labels={**s["labels"], "partially_seen_d": False},
             size_check={**s["size_check"], "result_path": "x", "result_sha256": "0" * 64})
    s["v"] = {**s["v"], "c_v": 0.1, "s_v": 0.3, "terciles": [0.0, 0.1], "tercile_gap": 2.2, "exclude_family": ""}
    s["e022"] = {**s["e022"], "registered": True, "dropped": None}  # registered but no END_UTC and no pin commit time: both are required
    assert {"e022.end_utc", "e022.pin_commit_utc"} <= set(lt.unfilled(s))
    s["e022"].update(end_utc="2026-11-16T00:00:00Z", pin_commit_utc="2026-11-17T09:00:00Z", analysis_job_start_utc="2026-11-17T05:00:00Z")
    assert lt.unfilled(s) == []
    with pytest.raises(RuntimeError, match="freeze condition"):  # pin after T_E022: V must be dropped before the pin
        lt.enforce_v_freeze(s)
    s["e022"]["pin_commit_utc"] = "2026-11-10T09:00:00Z"
    assert lt.enforce_v_freeze(s)["ok"]
    s["k_tests"] = ["K"]
    s["e022"]["pin_commit_utc"] = "2026-11-17T09:00:00Z"
    assert lt.enforce_v_freeze(s) is None  # V already dropped: nothing to enforce


# --- registration dates and V's E022 freeze condition --------------------------------------------------------------------


def test_registered_utc_rule_proposed_and_sliding():
    r = lt.registered_utc_rule(commit_utc="2026-11-01T10:00:00Z", lt5_registered_utc="2026-10-30T00:00:00Z", e022_end_utc="2026-11-16T00:00:00Z", e022_registered=True)
    assert (r["registered_utc"], r["end_utc"], r["analysis_not_before"]) == ("2026-11-16T00:00:00Z", "2026-12-07T00:00:00Z", "2026-12-08T12:00:00Z")
    # the family slides with E022: a later END_UTC moves everything by the rule; an END_UTC not at midnight rounds up to the next 00:00Z
    r = lt.registered_utc_rule(commit_utc="2026-11-01T10:00:00Z", lt5_registered_utc="2026-10-30T00:00:00Z", e022_end_utc="2026-11-20T00:00:00Z", e022_registered=True)
    assert r["registered_utc"] == "2026-11-20T00:00:00Z" and r["end_utc"] == "2026-12-11T00:00:00Z" and r["analysis_not_before"] == "2026-12-12T12:00:00Z"
    r = lt.registered_utc_rule(commit_utc="2026-11-01T10:00:00Z", lt5_registered_utc="2026-10-30T00:00:00Z", e022_end_utc="2026-11-16T02:31:00Z", e022_registered=True)
    assert r["registered_utc"] == "2026-11-17T00:00:00Z"


def test_registered_utc_rule_other_bounds_and_refusal():
    # (a) 24 h after the commit; (b) 48 h after LT5; (d) the 11-16 floor even with E022 dropped
    r = lt.registered_utc_rule(commit_utc="2026-11-20T01:00:00Z", lt5_registered_utc="2026-10-30T00:00:00Z")
    assert r["registered_utc"] == "2026-11-22T00:00:00Z"
    r = lt.registered_utc_rule(commit_utc="2026-11-01T10:00:00Z", lt5_registered_utc="2026-11-20T00:00:00Z")
    assert r["registered_utc"] == "2026-11-22T00:00:00Z"
    r = lt.registered_utc_rule(commit_utc="2026-11-01T10:00:00Z", lt5_registered_utc="2026-10-30T00:00:00Z")
    assert r["registered_utc"] == "2026-11-16T00:00:00Z"
    # a commit exactly 24 h before midnight is allowed (at least 24 h)
    r = lt.registered_utc_rule(commit_utc="2026-11-19T00:00:00Z", lt5_registered_utc="2026-10-30T00:00:00Z")
    assert r["registered_utc"] == "2026-11-20T00:00:00Z"
    with pytest.raises(ValueError, match="E022"):
        lt.registered_utc_rule(commit_utc="2026-11-01T10:00:00Z", lt5_registered_utc="2026-10-30T00:00:00Z", e022_registered=True)


def test_v_freeze_refuses_a_pin_after_either_e022_time():
    kw = dict(e022_registered=True)
    job, commit = "2026-11-17T08:00:00Z", "2026-11-17T12:00:00Z"
    assert lt.t_e022(job, commit).isoformat().startswith("2026-11-17T08:00:00")
    assert lt.v_freeze_check(pin_commit_utc="2026-11-10T00:00:00Z", analysis_job_start_utc=job, analysis_commit_utc=commit, **kw)["ok"]
    # after the job start but before the commit: refuses (the response had loosened it to the commit)
    r = lt.v_freeze_check(pin_commit_utc="2026-11-17T09:00:00Z", analysis_job_start_utc=job, analysis_commit_utc=commit, **kw)
    assert not r["ok"] and r["t_e022"] == "2026-11-17T08:00:00Z"
    # after the commit that came first (job start later): refuses
    r = lt.v_freeze_check(pin_commit_utc="2026-11-17T09:00:00Z", analysis_job_start_utc="2026-11-17T20:00:00Z", analysis_commit_utc="2026-11-17T07:00:00Z", **kw)
    assert not r["ok"] and r["t_e022"] == "2026-11-17T07:00:00Z"
    # exactly at T_E022 refuses (strictly before)
    assert not lt.v_freeze_check(pin_commit_utc=job, analysis_job_start_utc=job, analysis_commit_utc=commit, **kw)["ok"]
    # only one of the two times exists: it binds
    assert not lt.v_freeze_check(pin_commit_utc="2026-11-17T09:00:00Z", analysis_job_start_utc=job, **kw)["ok"]
    assert not lt.v_freeze_check(pin_commit_utc="2026-11-17T13:00:00Z", analysis_commit_utc=commit, **kw)["ok"]
    # E022 registered but its analysis not started: allowed; E022 dropped: lapses; neither: LT6 cannot register
    assert lt.v_freeze_check(pin_commit_utc="2026-11-30T00:00:00Z", **kw)["ok"]
    assert lt.v_freeze_check(pin_commit_utc="2026-12-30T00:00:00Z", e022_registered=False, e022_dropped=True, analysis_commit_utc=commit)["ok"]
    assert not lt.v_freeze_check(pin_commit_utc="2026-11-01T00:00:00Z", e022_registered=False)["ok"]


def test_v_first_origin_needs_both_k_minus_1_inputs_after_e022_end():
    end = "2026-11-16T00:00:00Z"
    assert not lt.v_first_origin_ok("2026-11-15T22:31:00Z", "2026-11-15T22:31:20Z", end)  # k = 00:31 pass
    assert not lt.v_first_origin_ok("2026-11-16T00:31:00Z", "2026-11-15T23:59:00Z", end)  # sweep before the end
    assert lt.v_first_origin_ok("2026-11-16T00:31:00Z", "2026-11-16T00:33:00Z", end)  # k = 02:31 pass
    assert not lt.v_first_origin_ok("2020-01-01T00:00:00Z", "2020-01-01T00:00:00Z", None)  # unknown END_UTC fails closed
    assert lt.v_first_origin_ok("2020-01-01T00:00:00Z", "2020-01-01T00:00:00Z", None, e022_dropped=True)  # E022 dropped


# --- the pinned crypto classifier ----------------------------------------------------------------------------------------


@pytest.mark.parametrize("cat,present,sports,expect", [
    ("Crypto", True, 0, "crypto"), ("  CRYPTO  ", True, 0, "crypto"), ("crypto_5m", True, 0, "crypto"), ("Cryptocurrency", True, 0, "crypto"),
    ("politics", True, 0, "non_crypto"), ("Sports", True, 1, "non_crypto"),
    (None, True, 0, "unknown"), ("", True, 0, "unknown"), ("   ", True, 0, "unknown"), (float("nan"), True, 0, "unknown"),
    ("nan", True, 0, "unknown"), ("None", True, 0, "unknown"), ("NULL", True, 0, "unknown"),
    ("crypto", False, 0, "unknown"), ("politics", True, -1, "unknown"),
])
def test_crypto_classifier(cat, present, sports, expect):
    assert lt.crypto_class(cat, present, sports) == expect


def test_unknown_counts_as_crypto_in_the_gate_numerator():
    r = lt.crypto_gate_share(["crypto", "unknown", "non_crypto", "non_crypto"])
    assert r["crypto"] == 1 and r["unknown"] == 1 and r["share_as_crypto"] == 0.5
    assert math.isnan(lt.crypto_gate_share([])["share_as_crypto"])


def test_crypto_failsafe_when_no_value_contains_crypto():
    bad = lt.crypto_failsafe({"politics": 10, "Sports": 5, None: 3})
    assert bad["classifier_shown_to_work"] is False and math.isnan(bad["gate_value"])
    ok = lt.crypto_failsafe({"politics": 10, "Crypto": 2})
    assert ok["classifier_shown_to_work"] is True and ok["distinct_values"]["Crypto"] == 2
    assert lt.crypto_failsafe(["a", "CRYPTO_x"])["classifier_shown_to_work"] is True


# --- K: the declared greedy train algorithm, one test per branch ---------------------------------------------------------


def _rows(ts, size="10", tx=None, asset="a", price="0.5") -> pd.DataFrame:
    n = len(ts)
    sizes = size if isinstance(size, list) else [size] * n
    assets = asset if isinstance(asset, list) else [asset] * n
    txs = tx if tx is not None else [f"t{i}" for i in range(n)]
    return pd.DataFrame({"ts": ts, "asset": assets, "size": sizes, "tx_hash": txs, "price": [price] * n})


def _trains(rows, min_size="1", **kw):
    res = lt.clip_trains(rows, min_size, _spec(), **kw)
    return [list(t) for t in res["trains"]], res


def test_k_skips_rows_under_two_seconds_and_leaves_them_unassigned():
    tr, res = _trains(_rows([0, 10, 10.5, 20, 30]))
    assert tr == [[0, 1, 3, 4]] and res["train_id"][2] == -1


def test_k_skips_a_repeated_tx_hash():
    tr, res = _trains(_rows([0, 10, 15, 20, 30], tx=["a", "b", "b", "c", "d"]))  # row 2 repeats row 1's tx: skipped (gap 5 would have fit)
    assert tr == [[0, 1, 3, 4]] and res["train_id"][2] == -1


def test_k_first_gap_any_within_the_span_then_band_applies():
    tr, _ = _trains(_rows([0, 500, 1000]))  # first gap 500 is accepted whatever it is; the second is in [0.5, 1.5] x 500
    assert tr == [[0, 1, 2]]
    tr, _ = _trains(_rows([0, 500, 1300]))  # second gap 800 > 750: closes with two rows, so no train
    assert tr == []


def test_k_band_is_inclusive_and_closes_outside():
    tr, _ = _trains(_rows([0, 10, 20, 30, 100]))
    assert tr == [[0, 1, 2, 3]]  # gap 70 is outside [5, 15]
    tr, _ = _trains(_rows([0, 10, 25]))  # gap 15 = 1.5 x 10: inside (inclusive)
    assert tr == [[0, 1, 2]]
    tr, _ = _trains(_rows([0, 10, 15]))  # gap 5 = 0.5 x 10: inside (inclusive)
    assert tr == [[0, 1, 2]]
    tr, _ = _trains(_rows([0, 10, 25.1]))  # 15.1 > 15
    assert tr == []
    tr, _ = _trains(_rows([0, 10, 14.9]))  # 4.9 < 5
    assert tr == []


def test_k_band_uses_the_median_of_the_runs_current_gaps_even_count_averaged():
    # gaps 10 and 14 -> median 12 (the average of the two middle gaps) -> band [6, 18]
    assert _trains(_rows([0, 10, 24, 42]))[0] == [[0, 1, 2, 3]]  # gap 18 = 1.5 x 12: inside
    assert _trains(_rows([0, 10, 24, 43]))[0] == [[0, 1, 2]]  # gap 19 > 18: the run closes at three rows, which is a train
    assert _trains(_rows([0, 10, 24, 29.9]))[0] == [[0, 1, 2]]  # gap 5.9 < 6
    # with three gaps 10, 14, 18 the median is 14 (odd count): band [7, 21]
    assert _trains(_rows([0, 10, 24, 42, 62]))[0] == [[0, 1, 2, 3, 4]]
    assert _trains(_rows([0, 10, 24, 42, 63.5]))[0] == [[0, 1, 2, 3]]  # gap 21.5 > 21


def test_k_closes_on_the_30_minute_span_inclusive():
    tr, _ = _trains(_rows([0, 600, 1200, 1800, 2400]))
    assert tr == [[0, 1, 2, 3]]  # span 1800 allowed, 2400 closes
    tr, _ = _trains(_rows([0, 600, 1200, 1801]))
    assert tr == [[0, 1, 2]]
    tr, _ = _trains(_rows([0, 1801, 3600]))  # even the first gap must keep the span <= 30 minutes
    assert tr == []


def test_k_short_run_restarts_at_i_plus_one():
    tr, _ = _trains(_rows([0, 10, 500, 510, 520]))
    assert tr == [[2, 3, 4]]  # the run [0, 1] closes at 500 (short); the next run starts at row 1, then row 2


def test_k_restarts_after_a_train_and_trains_never_overlap():
    tr, res = _trains(_rows([0, 10, 20, 5000, 5010, 5020]))
    assert tr == [[0, 1, 2], [3, 4, 5]]
    ids = res["train_id"]
    assert list(ids) == [0, 0, 0, 1, 1, 1]
    assert sum(len(t) for t in tr) == len(set(i for t in tr for i in t))


def test_k_run_end_of_group_closes():
    tr, _ = _trains(_rows([0, 10, 20]))
    assert tr == [[0, 1, 2]]
    assert _trains(_rows([0, 10]))[0] == []


def test_k_groups_by_asset_and_exact_size_in_decimal():
    # same size on two assets never joins; "10", "10.0" and "1E+1" are one key; "10.000001" is another
    rows = _rows([0, 10, 20, 30], size=["10", "10.0", "1E+1", "10.000001"])
    assert _trains(rows)[0] == [[0, 1, 2]]
    rows = _rows([0, 10, 20], asset=["a", "b", "a"])
    assert _trains(rows)[0] == []
    assert lt.size_key("10") == lt.size_key("10.0") == lt.size_key("1E+1") != lt.size_key("10.000001")
    assert lt.size_key("abc") is None and lt.size_key("NaN") is None
    assert lt.size_from_json_number("10.10") == Decimal("10.10")


def test_k_no_float_rounding_merges_sizes():
    a, b = "0.30000000000000004", "0.3"
    assert lt.size_key(a) != lt.size_key(b) and float(a) != 0.3
    assert _trains(_rows([0, 10, 20], size=[a, b, a]), min_size="0.01")[0] == []


def test_k_min_size_exclusion_is_in_decimal_two_times_the_sidecar_value():
    rows = _rows([0, 10, 20, 30], size=["10", "10", "10", "10"])
    assert _trains(rows, min_size="5")[0] == []  # 10 <= 2 x 5: removed first
    tr, res = _trains(rows, min_size="4.99999999999999999999")  # 9.99999999999999999998 < 10 in Decimal (a float would call them equal)
    assert tr == [[0, 1, 2, 3]] and not res["removed_min_size"].any()
    assert lt.min_size_cutoff("5") == Decimal("10")
    assert lt.min_size_cutoff(None) is None and lt.min_size_cutoff("x") is None and lt.min_size_cutoff("0") is None
    unknown = lt.clip_trains(rows, None, _spec())
    assert unknown["cutoff_unknown"] and unknown["n_trains"] == 0


def test_k_bad_size_rows_are_excluded_and_counted():
    res = lt.clip_trains(_rows([0, 10, 20, 30], size=["10", "x", "10", "10"]), "1", _spec())
    assert res["bad_size"].tolist() == [False, True, False, False] and res["trains"] == [[0, 2, 3]]


def test_k_ties_in_ts_break_by_tx_hash_and_equal_second_rows_are_skipped():
    # two prints in the same second are race fingerprints: the second is skipped (gap < 2 s)
    rows = _rows([0, 0, 10, 20], tx=["b", "a", "c", "d"])
    res = lt.clip_trains(rows, "1", _spec())
    assert res["trains"] == [[1, 2, 3]] and res["train_id"][0] == -1  # sorted by (ts, tx_hash): "a" first


def test_k_ts_as_strings_and_floats_agree():
    a = lt.clip_trains(_rows([0, 10, 20]), "1", _spec())["trains"]
    b = lt.clip_trains(_rows(["0", "10", "20"]), "1", _spec())["trains"]
    c = lt.clip_trains(_rows([0.0, 10.0, 20.0]), "1", _spec())["trains"]
    assert a == b == c == [[0, 1, 2]]


def test_k_unit_features_shares_and_age():
    # 3 clip rows (size 10, price .5 -> notional 5 each) + 1 non-clip row of size 25 (notional 12.5) + 1 min-size row (size 1, notional .5)
    rows = _rows([100, 110, 120, 130, 140], size=["10", "10", "10", "25", "1"], price="0.5")
    rows.loc[3, "ts"], rows.loc[4, "ts"] = 700, 705
    f = lt.clip_unit_features(rows, "1", t_k=1000.0, spec=_spec())
    tot = 15 + 12.5 + 0.5
    assert f["n_int"] == 5 and f["n_trains"] == 1
    assert f["clip_share"] == pytest.approx(15 / tot)
    assert f["minsize_share"] == pytest.approx(0.5 / tot)
    assert f["round_share"] == pytest.approx(15 / tot)  # the three size-10 rows are multiples of 10
    assert f["last_clip_age"] == 1000 - 120
    assert lt.clip_class(f["clip_share"], _spec()) == "clip"
    assert lt.clip_class(0.0, _spec()) == "clip_free" and lt.clip_class(0.1, _spec()) == "interior" and lt.clip_class(0.25, _spec()) == "clip"
    assert lt.clip_class(float("nan"), _spec()) == "nan"


def test_k_unit_features_unsigned_share_and_would_be_notional_before_exclusion():
    rows = _rows([0, 10, 20, 3000], size=["1", "1", "1", "7"], price="1")
    f = lt.clip_unit_features(rows, "1", t_k=4000.0, spec=_spec())
    assert f["n_trains"] == 0 and f["clip_share"] == 0.0  # size 1 <= 2 x 1: all removed
    assert f["would_be_clip_notional"] == pytest.approx(3.0) and f["would_be_clip_notional_minsize"] == pytest.approx(3.0)
    assert f["H_unsigned"] == pytest.approx(3.0 / 10.0)  # the three rows within 300 s of one another
    assert f["minsize_share"] == pytest.approx(3.0 / 10.0)


def test_k_rows_at_or_after_the_decision_time_are_never_read():
    tr = _rows([100, 110, 120, 999.999, 1000, 1000.5], size=["10"] * 6)
    sub = lt.interval_rows(tr, 100.0, 1000.0)
    assert sub["ts"].tolist() == [100, 110, 120, 999.999]
    known = np.array([True, False, True, True, True, True])
    assert lt.interval_rows(tr, 100.0, 1000.0, known)["ts"].tolist() == [100, 120, 999.999]


def test_k_near_identical_placebo_grouping_is_deterministic():
    rows = _rows([0, 10, 20, 30, 40, 50], size=["100", "103", "104.9", "104.9", "106", "200"])
    keys = lt.near_identical_keys(rows)
    # sorted by size: 100, 103, 104.9, 104.9(identical: closes), 106 (within 5% of 104.9), 200
    assert keys[0] == keys[1] == keys[2] != keys[3]
    assert keys[3] == keys[4] != keys[5]
    assert keys == lt.near_identical_keys(rows)
    # the group is the placebo's "size": the same train rule runs on it, and identical-size rows never share a group
    res = lt.clip_trains(_rows([0, 10, 20], size=["100", "103", "104"]), "1", _spec(), keys=lt.near_identical_keys(_rows([0, 10, 20], size=["100", "103", "104"])))
    assert res["trains"] == [[0, 1, 2]]
    res = lt.clip_trains(_rows([0, 10, 20], size=["100", "100", "100"]), "1", _spec(), keys=lt.near_identical_keys(_rows([0, 10, 20], size=["100", "100", "100"])))
    assert res["trains"] == []  # three identical sizes land in three groups under the placebo grouping


# --- V -------------------------------------------------------------------------------------------------------------------


def _u(x, **k) -> pd.DataFrame:
    base = dict(x=x, dbid5_k=[100.0] * len(x), dask5_k=[50.0] * len(x), dbid5_p=[60.0] * len(x), dask5_p=[60.0] * len(x),
                dbid1_k=[10.0] * len(x), dask1_k=[10.0] * len(x), dbid1_p=[10.0] * len(x), dask1_p=[10.0] * len(x),
                sbid_k=[0.4] * len(x), sask_k=[0.6] * len(x), liq=[1000.0] * len(x))
    base.update(k)
    return pd.DataFrame(base)


def test_v_imbalance_orientation_and_sign():
    assert lt.imbalance([100], [50])[0] == pytest.approx(1 / 3)
    assert np.isnan(lt.imbalance([0], [0])[0]) and np.isnan(lt.imbalance([np.nan], [5])[0])
    o = lt.v_fields(_u([0.02, -0.02]))
    # bids stacked (imb > 0): aligned with a rise, against a fall
    assert o["v"].tolist() == pytest.approx([1 / 3, -1 / 3])
    assert o["v_prev"].tolist() == pytest.approx([0.0, -0.0])
    assert np.allclose(o["sx"], [1, -1])


def test_v_prev_comes_from_the_k_minus_1_sweep():
    o = lt.v_fields(_u([0.02, -0.02], dbid5_p=[90.0, 90.0], dask5_p=[10.0, 10.0]))
    assert o["v_prev"].tolist() == pytest.approx([0.8, -0.8])


def test_v_toward_away_sides_and_log_ratios():
    t, a = lt.toward_away([1, -1], [100, 100], [30, 30])
    assert t.tolist() == [30, 100] and a.tolist() == [100, 30]  # toward = asks for a rise, bids for a fall
    o = lt.v_fields(_u([0.02, -0.02], dbid5_k=[100.0, 100.0], dask5_k=[30.0, 30.0], dbid5_p=[100.0, 100.0], dask5_p=[60.0, 60.0]))
    assert o["lt"].iloc[0] == pytest.approx(math.log(31 / 61))  # rise: toward = ask depth, 60 -> 30
    assert o["la"].iloc[0] == pytest.approx(0.0)  # away = bid depth unchanged
    assert o["lt"].iloc[1] == pytest.approx(0.0) and o["la"].iloc[1] == pytest.approx(math.log(31 / 61))  # fall: toward = bids (unchanged)


def test_v_hollowness_on_outcome_0_notional():
    o = lt.v_fields(_u([0.02], dbid5_k=[100.0], dask5_k=[50.0], liq=[1000.0]))
    assert o["h0"].iloc[0] == pytest.approx(1 - (100 * 0.4 + 50 * 0.6) / 1000)
    assert lt.v_fields(_u([0.02], liq=[10.0]))["h0"].iloc[0] == 0.0  # clipped at 0
    assert np.isnan(lt.v_fields(_u([0.02], liq=[0.0]))["h0"].iloc[0])
    assert np.isnan(lt.v_fields(_u([0.02], liq=[np.nan]))["h0"].iloc[0])


def test_v_target_is_signed_skip_from_pass_k_plus_1():
    assert lt.v_target([0.5], [0.53], [1])[0] == pytest.approx(0.03)
    assert lt.v_target([0.5], [0.53], [-1])[0] == pytest.approx(-0.03)


def test_v_depletion_gate_branches():
    g = _spec()["census_gates"]["CV_V"]
    # 10 rises, 1c ask (toward) depth halved in 6, bid (away) depth halved in 1 -> asymmetry 0.5 > 20 pp: fails
    n = 10
    d = _u([0.02] * n, dask1_k=[4.0] * 6 + [10.0] * 4, dbid1_k=[4.0] + [10.0] * 9)
    r = lt.depletion_gate(d, g)
    assert r["toward_halved_1c"] == pytest.approx(0.6) and r["away_halved_1c"] == pytest.approx(0.1)
    assert r["asym_pp"] == pytest.approx(0.5) and r["pass_1c"] is False
    # symmetrical depletion passes the 1c asymmetry even if both are large
    d = _u([0.02] * n, dask1_k=[4.0] * 8 + [10.0] * 2, dbid1_k=[4.0] * 8 + [10.0] * 2)
    assert lt.depletion_gate(d, g)["pass_1c"] is True
    # exactly at the limit passes (<=): 3 of 10 toward, 1 of 10 away -> 0.2
    d = _u([0.02] * n, dask1_k=[4.0] * 3 + [10.0] * 7, dbid1_k=[4.0] + [10.0] * 9)
    r = lt.depletion_gate(d, g)
    assert r["asym_pp"] == pytest.approx(0.2) and r["pass_1c"] is True


def test_v_depletion_gate_excludes_zero_prev_units_from_both_shares():
    g = _spec()["census_gates"]["CV_V"]
    d = _u([0.02] * 4, dask1_p=[0.0, 10.0, 10.0, 10.0], dask1_k=[0.0, 4.0, 10.0, 10.0])
    r = lt.depletion_gate(d, g)
    assert r["n_1c"] == 3 and r["n_1c_excluded_zero_prev"] == 1
    # the away (bid) side zero in k - 1 excludes too
    d = _u([0.02] * 4, dbid1_p=[0.0, 10.0, 10.0, 10.0])
    assert lt.depletion_gate(d, g)["n_1c_excluded_zero_prev"] == 1


def test_v_depletion_gate_5c_toward_share_and_nan_fails():
    g = _spec()["census_gates"]["CV_V"]
    d = _u([0.02] * 10, dask5_k=[10.0] * 6 + [60.0] * 4, dask5_p=[60.0] * 10)  # toward (ask) 5c halved in 6 of 10 -> 0.6 > 0.5
    r = lt.depletion_gate(d, g)
    assert r["toward_halved_5c"] == pytest.approx(0.6) and r["pass_5c"] is False
    assert r["round_original_toward_below_prev_5c"] == pytest.approx(0.6)
    e = lt.depletion_gate(_u([0.02] * 3, dask1_k=[np.nan] * 3, dask1_p=[np.nan] * 3, dask5_k=[np.nan] * 3), g)
    assert e["pass_1c"] is False and e["pass_5c"] is False  # NaN fails


# --- D --------------------------------------------------------------------------------------------------------------------


def test_parse_end_date_rules():
    assert lt.parse_end_date("2026-11-01T12:00:00Z") == datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
    assert lt.parse_end_date("2026-11-01T12:00:00+00:00") == lt.parse_end_date("2026-11-01T12:00:00Z")
    assert lt.parse_end_date("2026-11-01T12:00:00") == datetime(2026, 11, 1, 12, 0, tzinfo=UTC)  # naive = UTC
    assert lt.parse_end_date("2026-11-01T08:00:00-04:00") == datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
    assert lt.parse_end_date("2026-11-01T12:00:00.750Z") == datetime(2026, 11, 1, 12, 0, tzinfo=UTC)  # equal to the second
    for bad in ("2026-11-01", " 2026-11-01 ", "garbage", "", None, float("nan"), "2026-13-01T00:00:00Z"):
        assert lt.parse_end_date(bad) is None


@pytest.mark.parametrize("utc,expect", [
    ("2026-10-31T03:59:00Z", True),  # 23:59 EDT (UTC-4) on 10-30
    ("2026-11-02T04:59:00Z", True),  # 23:59 EST (UTC-5) after the 11-01 DST change
    ("2026-11-02T03:59:00Z", False),  # 22:59 EST: would be 23:59 only if DST were wrongly kept
    ("2026-11-02T05:00:00Z", True),  # 00:00 EST
    ("2026-11-01T04:00:00Z", True),  # 00:00 EDT on 11-01
    ("2026-11-01T03:58:00Z", True),  # 23:58:00 EDT = 1 minute before 23:59:00 (inclusive)
    ("2026-11-01T03:57:59Z", False),
    ("2026-11-01T04:01:00Z", True),  # 00:01:00 EDT (inclusive)
    ("2026-11-01T04:01:01Z", False),
    ("2026-11-01T16:00:00Z", False),
])
def test_bydate_template_across_the_dst_change(utc, expect):
    assert lt.bydate_template(lt.parse_end_date(utc)) is expect
    assert lt.bydate_template(None) is None


T_K = datetime(2026, 11, 20, 12, 0, tzinfo=UTC).timestamp()


def _cls(old, new, slugs=False, t_k=T_K):
    return lt.end_change_class(old, new, t_k, slugs, _spec())


def test_d_change_classes():
    old = "2026-12-31T04:59:00Z"
    assert _cls(old, old)["cls"] == "no_change"
    assert _cls(old, "2026-12-31T04:59:00+00:00")["cls"] == "no_change"  # byte-different, equal after parse
    assert _cls(old, "2026-12-31T04:59:00.9Z")["cls"] == "no_change"  # equal to the second
    assert _cls(old, "2027-01-31T04:59:00Z")["cls"] == "later"
    assert _cls(old, "2026-12-31T05:59:00Z")["cls"] == "later"  # exactly 1 h
    assert _cls(old, "2026-12-31T05:58:59Z")["cls"] == "small"  # 59 min 59 s
    assert _cls(old, "2026-12-31T04:00:00Z")["cls"] == "small"  # earlier by under 1 h
    assert _cls(old, "2026-12-30T04:59:00Z")["cls"] == "earlier"
    assert _cls(old, "2026-12-31")["cls"] == "unparseable"  # a date-only end is never "unchanged"
    assert _cls("garbage", old)["cls"] == "unparseable" and _cls(None, old)["cls"] == "unparseable"
    c = _cls(old, "2027-01-31T04:59:00Z")
    assert c["bydate"] is True and c["delta_s"] == 31 * 86400 and c["T_new_h"] == pytest.approx((datetime(2027, 1, 31, 4, 59, tzinfo=UTC).timestamp() - T_K) / 3600)


def test_d_overdue_and_rollover_exclusions():
    # old end <= t_k: an overdue extension (CH189's object), excluded from the primary
    assert _cls("2026-11-20T11:59:00Z", "2026-12-20T11:59:00Z")["cls"] == "overdue"
    assert _cls("2026-11-20T12:00:00Z", "2026-12-20T12:00:00Z")["cls"] == "overdue"  # old == t_k counts
    # series roll-overs: non-empty slugs and |delta| within 1 h of 1, 7, 30 or 31 days
    old = "2026-12-31T04:59:00Z"
    for days in (1, 7, 30, 31):
        new = datetime.fromtimestamp(datetime(2026, 12, 31, 4, 59, tzinfo=UTC).timestamp() + days * 86400 + 3600, UTC).isoformat()
        assert _cls(old, new, slugs=True)["cls"] == "rollover"
        assert _cls(old, new, slugs=False)["cls"] == "later"  # no series slug: not a roll-over
    assert _cls(old, "2027-01-02T04:59:00Z", slugs=True)["cls"] == "later"  # 2 days: not a roll-over delta
    assert _cls(old, "2027-01-01T06:00:00Z", slugs=True)["cls"] == "later"  # 1 d + 1 h 1 min: outside the tolerance


def test_d_theta24_formula():
    m, T = 0.5, 48.0
    assert lt.theta24([m], [T])[0] == pytest.approx(24 * 0.5 * math.log(0.5) / 48)
    assert lt.theta24([0.5], [96.0])[0] > lt.theta24([0.5], [48.0])[0]  # a later deadline slows the (negative) decay
    assert np.isnan(lt.theta24([0.5], [0.0])[0]) and np.isnan(lt.theta24([1.0], [10.0])[0])


# --- washout --------------------------------------------------------------------------------------------------------------


def test_washout_slots_k_plus_1_to_k_plus_11():
    slots = np.arange(100, 120)
    w = lt.washout(slots, [105])
    assert slots[w].tolist() == list(range(106, 117))  # k + 1 .. k + 11
    assert not w[slots == 105].any() and not w[slots == 117].any() and not w[slots == 104].any()
    assert lt.washout(slots, []).sum() == 0 and lt.washout([], [3]).sum() == 0
    # look-back labelled slots (before the window) wash out the first window units
    assert lt.washout([100, 101], [95, 90]).tolist() == [True, True]
    assert lt.washout([107], [95]).tolist() == [False]  # 12 slots after: clean


# --- B --------------------------------------------------------------------------------------------------------------------

TP, TK = 1000.0, 8200.0


def _nk(created, members=3, recurring=False):
    return lt.newcomer_kind(created_ts=created, t_prev=TP, t_k=TK, members_prev=members, recurring=recurring)


def test_newcomer_kinds():
    assert _nk(TP) == "birth" and _nk(TK - 1) == "birth"  # [t_prev, t_k)
    assert _nk(TK) == "lagged" and _nk(TP - 1) == "lagged"
    assert _nk(None) == "created_unparseable" and _nk(float("nan")) == "created_unparseable"
    assert _nk(TP + 5, members=1) == "not_existing"
    assert _nk(TP + 5, recurring=True) == "recurring"
    assert _nk(TP - 5, recurring=True, members=0) == "lagged"  # a lagged appearance is reported as such first


def _n(kind, t=100.0):
    return {"kind": kind, "t_row": t}


def test_incumbent_classes_clean_no_birth_and_exclusions():
    assert lt.incumbent_birth_class([], 100.0) == {"cls": "nobirth", "reason": "", "n_born": 0}
    assert lt.incumbent_birth_class([_n("birth", 103.0)], 100.0)["cls"] == "birth"
    assert lt.incumbent_birth_class([_n("birth", 105.0)], 100.0)["cls"] == "birth"  # exactly 5 s is inside
    g = lt.incumbent_birth_class([_n("birth", 105.1)], 100.0)
    assert g["cls"] == "excluded" and g["reason"] == "guard_loss"  # a newcomer received > 5 s after the incumbent cannot label it
    assert lt.incumbent_birth_class([_n("birth", 90.0)], 100.0)["cls"] == "birth"  # newcomer row received earlier: fine
    # a lagged appearance alone is excluded, never class 0
    l_ = lt.incumbent_birth_class([_n("lagged")], 100.0)
    assert l_["cls"] == "excluded" and l_["reason"] == "lagged_only"
    assert lt.incumbent_birth_class([_n("not_existing")], 100.0)["reason"] == "lagged_only"
    assert lt.incumbent_birth_class([_n("created_unparseable")], 100.0)["reason"] == "created_unparseable"
    assert lt.incumbent_birth_class([_n("recurring")], 100.0)["reason"] == "recurring_newcomer"
    # a lagged appearance next to a true birth: still a birth; unparseable / recurring next to a birth: excluded (stricter)
    assert lt.incumbent_birth_class([_n("birth", 101.0), _n("lagged")], 100.0)["cls"] == "birth"
    assert lt.incumbent_birth_class([_n("birth", 101.0), _n("recurring")], 100.0)["reason"] == "recurring_newcomer"
    assert lt.incumbent_birth_class([_n("birth", 101.0), _n("created_unparseable")], 100.0)["reason"] == "created_unparseable"


def test_several_newcomers_are_one_birth_and_every_row_must_pass_the_guard():
    r = lt.incumbent_birth_class([_n("birth", 101.0), _n("birth", 102.0), _n("birth", 103.0)], 100.0)
    assert r["cls"] == "birth" and r["n_born"] == 3
    r = lt.incumbent_birth_class([_n("birth", 101.0), _n("birth", 111.0)], 100.0)
    assert r["cls"] == "excluded" and r["reason"] == "guard_loss" and r["n_born"] == 2


def test_fake_birth_draw_is_seeded_distant_and_tercile_matched():
    window = list(range(0, 60))
    terc = {s: (s % 3) for s in window}
    real = [10, 40]
    seen = set()
    for seed in range(20):
        s = lt.fake_birth_slot(real, window, terc, 2, np.random.default_rng(seed))
        assert s is not None and all(abs(s - r) >= 12 for r in real) and terc[s] == 2
        seen.add(s)
    assert len(seen) > 1
    a = lt.fake_birth_slot(real, window, terc, 2, np.random.default_rng(20261364))
    assert a == lt.fake_birth_slot(real, window, terc, 2, np.random.default_rng(20261364))
    assert lt.fake_birth_slot([10], list(range(8, 14)), {s: 0 for s in range(8, 14)}, 0, np.random.default_rng(1)) is None  # none qualifies
    assert lt.fake_birth_slot([10], window, {s: 0 for s in window}, 1, np.random.default_rng(1)) is None  # none in the tercile


def test_k_features_freeze_the_p1_placebo_and_s3_notional_clips():
    """Freeze-check fix (HIGH): P1 and S3 cannot be recomputed after the trade samples rotate off, so the reader freezes them."""
    # P1: near-identical (never identical) sizes 100, 103, 104 at a regular rhythm: a placebo train, and NOT a real clip train
    rows = _rows([100, 110, 120], size=["100", "103", "104"], price="0.5")
    f = lt.clip_unit_features(rows, "1", t_k=1000.0, spec=_spec())
    assert f["clip_share"] == 0.0 and f["p1_n_trains"] == 1 and f["p1_clip_share"] == pytest.approx(1.0)
    # identical sizes are a real clip train and give the placebo nothing
    g = lt.clip_unit_features(_rows([100, 110, 120], size=["10", "10", "10"], price="0.5"), "1", t_k=1000.0, spec=_spec())
    assert g["clip_share"] == pytest.approx(1.0) and g["p1_n_trains"] == 0 and g["p1_clip_share"] == 0.0
    # S3: sizes and prices differ but size x price is identical to the cent (10 x 0.5 = 20 x 0.25 = 5)
    r = _rows([100, 110, 120], size=["10", "20", "5"], price="0.5")
    r["price"] = ["0.5", "0.25", "1"]
    h = lt.clip_unit_features(r, "1", t_k=1000.0, spec=_spec())
    assert h["clip_share"] == 0.0 and h["s3_n_trains"] == 1 and h["s3_clip_share"] == pytest.approx(1.0)
    assert lt.notional_cent_keys(r) == [Decimal("5.00")] * 3
