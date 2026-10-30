# ruff: noqa: E501
"""LT12 census CC12 (LIVE_TESTS_12.md 7), synthetic capture and feed trees only (no host data, no network): the fresh seal and its refusals, the input
identity check, the minimum covered days checked FIRST (no row opened), CH244's feed coverage checked first in its block (re-check fix 3:
``census_unavailable (coverage)`` before any other CH244 gate value), the feed-listed share gate (``census_dropped``), single-threshold flips of the gate
blocks, the exhaustive census-fixed list (item 9 ``rho_census`` included), the lag-slot loader as the only later-slot reader, and the header pre-check."""

from __future__ import annotations

import copy
import json
from datetime import timedelta
from pathlib import Path

import pytest

from astrolabe.research_lab import live_tests12 as lt
from tests import lt12_synth as sy

SLOTS = range(0, 46)


@pytest.fixture(scope="module")
def tree(tmp_path_factory):
    root = tmp_path_factory.mktemp("lt12census")
    snap, feed = root / "snap", root / "feed"
    by = sy.rich_world(snap, SLOTS, feed_root=feed)
    return {"root": root, "snap": snap, "feed": feed, "by_slot": by}


def _seal(tree, spec: dict, tmp_path: Path, feed=None, name: str = "seal.json") -> Path:
    s = lt.seal_inputs(snapshot_root=[tree["snap"]], feed_root=feed if feed is not None else tree["feed"], work=tmp_path / "sw", spec=spec)
    assert "error" not in s, s.get("error")
    p = tmp_path / name
    p.write_text(json.dumps(s, default=str))
    return p


def _frozen_feed_gates(spec: dict) -> dict:
    """The loose test spec relaxes every minimum / maximum; the feed tests restore the frozen feed thresholds (coverage >= 0.5, listed share <= 0.20)."""
    g0 = lt.load_spec(sha=None)["census_gates"]["CH244"]
    assert g0["feed_coverage_min"] == 0.5 and g0["feed_listed_share_max"] == 0.2
    for k in ("feed_coverage_min", "feed_listed_share_max"):
        spec["census_gates"]["CH244"][k] = g0[k]
    return spec


def _census(tree, spec: dict, tmp_path: Path, feed=None) -> dict:
    p = _seal(tree, spec, tmp_path, feed=feed)
    return lt.census_captures(seal=p, snapshot_root=[tree["snap"]], feed_root=feed if feed is not None else tree["feed"], work=tmp_path / "cw", spec=spec)


def test_census_passes_on_the_rich_world_and_fixes_every_declared_value(tree, tmp_path):
    spec = sy.census_spec(14, 40)
    res = _census(tree, spec, tmp_path)
    assert res["statuses"] == {"CH245": lt.CENSUS_PASS, "CH244": lt.CENSUS_PASS}
    for t in lt.TESTS:
        assert set(lt.CENSUS_FIXED_KEYS[t]) <= set(res[t]["census_fixed"]), t
        assert "mde_c" in res[t]["census_gate_values"]
    cf = res["CH245"]["census_fixed"]
    assert isinstance(cf["rho_census"], float) and cf["rho_census_nan"] is False and -1 <= cf["rho_census"] <= 1  # item 9 (re-check fix 2)
    assert cf["s_D"] > 0 and cf["s_T"] > 0 and len(cf["zs_cuts"]) == 2 and cf["rgap_q50_s"] >= 0
    g245 = res["CH245"]["gate_CH245"]
    for gate in ("pair_completeness", "receipt_span", "thin_units", "distinct_events", "events_ge48", "g_eff", "same_slot", "ident_nonzero", "ident_top1", "ident_event", "vif_w",
                 "venue_clock", "block_share", "placebo_coverage", "r_gate", "slope_mde", "f_mde"):
        assert gate in g245, gate
    g244 = res["CH244"]["gate_CH244"]
    for gate in ("status_finite", "ladder_completeness", "receipt_span", "tested_units", "rewarded_shock_units", "feed_listed_share", "shock_share", "corr_unrew_liq",
                 "within_stratum", "vif_w", "distinct_events", "events_ge48", "g_eff", "venue_clock", "block_share", "r_gate", "class_mde", "f_mde"):
        assert gate in g244, gate
    assert {"carry_against_simple", "feed_table", "mixed_counts", "switch", "feed_age_h_quantiles"} <= set(res["CH244"])
    assert res["overlap"]["shared_events"] == 0  # two members against 3-10: disjoint by construction


def test_coverage_is_checked_first_and_no_row_is_opened(tree, tmp_path, monkeypatch):
    spec = sy.census_spec(14, 40)
    spec["census_inputs"]["min_covered_days"] = {"CC12": 99.0, "CC12_twins": 1.0}
    p = _seal(tree, spec, tmp_path)

    def boom(*a, **k):
        raise AssertionError("a capture row was opened before the coverage check")

    monkeypatch.setattr(lt, "load_rows12", boom)
    monkeypatch.setattr(lt, "write_series12", boom)
    res = lt.census_captures(seal=p, snapshot_root=[tree["snap"]], feed_root=tree["feed"], work=tmp_path / "cw", spec=spec)
    assert res["statuses"] == {"CH245": lt.CENSUS_UNAVAILABLE, "CH244": lt.CENSUS_UNAVAILABLE}
    assert "gate_CH245" not in json.dumps(res) and "gate_CH244" not in json.dumps(res)
    assert lt.CENSUS_UNAVAILABLE != lt.CENSUS_DROPPED


def test_ch244_feed_coverage_below_half_is_census_unavailable_before_any_other_gate_value(tree, tmp_path):
    spec = _frozen_feed_gates(sy.census_spec(14, 40))
    empty = tmp_path / "nofeed"
    empty.mkdir()
    res = _census(tree, spec, tmp_path, feed=empty)
    r = res["CH244"]
    assert r["status"] == lt.CENSUS_UNAVAILABLE and set(r) == {"covered_days", "twin_days", "feed_coverage", "status"}  # only the coverage counts
    assert r["feed_coverage"]["feed_coverage"] == 0.0 and r["feed_coverage"]["tested_units"] > 0
    assert res["CH245"]["status"] == lt.CENSUS_PASS  # the blocks are independent


def test_ch244_feed_listed_share_above_020_is_census_dropped(tree, tmp_path):
    feed = tmp_path / "feed_all"
    by = tree["by_slot"]
    import pandas as pd

    rows = pd.read_csv(by[20]["dir"] / "rows.csv.gz", dtype=str)
    every = {c: 10.0 for c in rows["condition_id"]}  # the feed lists EVERY member with a positive rate, unrewarded ones included
    for s in SLOTS:
        sy.write_feed(feed, sy.slot_dt(s) - timedelta(minutes=30), every)
    spec = _frozen_feed_gates(sy.census_spec(14, 40))
    res = _census(tree, spec, tmp_path, feed=feed)
    r = res["CH244"]
    assert r["feed_coverage"]["feed_coverage"] >= 0.5 and r["feed_listed_share"] > 0.20
    assert r["gate_CH244"]["feed_listed_share"] is False and r["status"] == lt.CENSUS_DROPPED


@pytest.mark.parametrize("test,key,value,gate", [("CH245", "placebo_coverage_min", 1.01, "placebo_coverage"), ("CH245", "units_projected_min", 1e12, "thin_units"),
                                                  ("CH245", "vif_w_max", 0.5, "vif_w"), ("CH244", "tested_units_projected_min", 1e12, "tested_units"),
                                                  ("CH244", "feed_listed_share_max", -1.0, "feed_listed_share"), ("CH244", "status_finite_min", 1.01, "status_finite")])
def test_one_threshold_flips_only_its_gate(tree, tmp_path, test, key, value, gate):
    spec = sy.census_spec(14, 40)
    spec["census_gates"][test][key] = value
    res = _census(tree, spec, tmp_path)
    g = res[test][f"gate_{test}"]
    assert g[gate] is False and res[test]["status"] == lt.CENSUS_DROPPED
    assert all(v for k_, v in g.items() if k_ not in (gate, "pass") and isinstance(v, bool))
    other = "CH244" if test == "CH245" else "CH245"
    assert res[other]["status"] == lt.CENSUS_PASS


def test_census_pass_reads_no_slot_after_the_origins_except_through_the_lag_loaders(tree, tmp_path, monkeypatch):
    spec = sy.census_spec(14, 40)
    reads, lag = [], []

    class Rec(lt.SlotStore):
        def _get(self, kind, j, fn):
            reads.append(j)
            return super()._get(kind, j, fn)

    monkeypatch.setattr(lt, "SlotStore", Rec)
    real = lt.lag_twin_zs
    monkeypatch.setattr(lt, "lag_twin_zs", lambda a, b_, *x, **k: lag.append((Path(a).name, Path(b_).name)) or real(a, b_, *x, **k))
    res = _census(tree, spec, tmp_path)
    assert res["statuses"]["CH245"] == lt.CENSUS_PASS
    assert max(reads) <= 40  # the last origin slot; k + 1 .. k + 3 never reach census code through the store
    ids = {v["id"]: k for k, v in tree["by_slot"].items()}
    assert lag and all(ids[b_] == ids[a] + 1 for a, b_ in lag)  # twins read captures k + 2 and k + 3 only


def test_seal_refusals(tree, tmp_path):
    spec = sy.census_spec(14, 40)
    other = tmp_path / "design.md"
    other.write_text("not the frozen text")
    assert "differs from the text-frozen file" in lt.seal_inputs(snapshot_root=[tree["snap"]], feed_root=tree["feed"], work=tmp_path / "w1", spec=spec, design_path=other)["error"]
    sp = copy.deepcopy(spec)
    sp["k_block"] = {"chg_1d": None, "chg_1w": None}
    assert "header pre-check" in lt.seal_inputs(snapshot_root=[tree["snap"]], work=tmp_path / "w2", spec=sp)["error"]
    sp = copy.deepcopy(spec)
    sp["reward_null_rule"] = "simple"
    assert "listed_carry24h_v2" in lt.seal_inputs(snapshot_root=[tree["snap"]], work=tmp_path / "w3", spec=sp)["error"]


def test_census_refuses_changed_spec_blocks_and_a_changed_input(tree, tmp_path):
    spec = sy.census_spec(14, 40)
    p = _seal(tree, spec, tmp_path)
    sp = copy.deepcopy(spec)
    sp["census_gates"]["CH245"]["vif_w_max"] = 3.0  # a threshold changed after the seal
    r = lt.census_captures(seal=p, snapshot_root=[tree["snap"]], feed_root=tree["feed"], work=tmp_path / "c1", spec=sp)
    assert "census blocks differ" in r["error"]
    seal = json.loads(p.read_text())
    rel = next(k for k, v in seal["files"].items() if v["kind"] == "capture")
    seal["files"][rel]["sha256"] = "0" * 64
    p2 = tmp_path / "seal2.json"
    p2.write_text(json.dumps(seal))
    r = lt.census_captures(seal=p2, snapshot_root=[tree["snap"]], feed_root=tree["feed"], work=tmp_path / "c2", spec=spec)
    assert "input identity" in r["error"]


def test_header_precheck_reads_headers_only(tree):
    cap = tree["by_slot"][20]["dir"]
    fd = sorted(Path(tree["feed"]).iterdir())[0]
    h = lt.header_precheck(capture_dir=cap, feed_dir=fd)
    assert h["chg_1d"] is True and h["chg_1w"] is True and h["rows_missing"] == [] and h["sidecar_missing"] == [] and h["feed_missing"] == []
    assert h["manifest_has_state"] is True
