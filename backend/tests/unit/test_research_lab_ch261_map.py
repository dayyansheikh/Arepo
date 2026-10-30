# ruff: noqa: E501
"""CH261 population map: synthetic captures only (no data-dumps reads)."""

from __future__ import annotations

import csv
import gzip
import importlib.util
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from astrolabe.research_lab import population_map_ch251 as c251
from astrolabe.research_lab import population_map_ch261 as m

_P = Path(__file__).resolve().parents[2] / "scripts" / "run_ch261_map.py"
_spec = importlib.util.spec_from_file_location("run_ch261_map_under_test", _P)
runner = importlib.util.module_from_spec(_spec)
sys.modules["run_ch261_map_under_test"] = runner
_spec.loader.exec_module(runner)

T0 = datetime(2026, 10, 16, 0, 31, tzinfo=UTC)
RCOLS = ["market_id", "event_id", "received_utc", "closed", "active", "binary", "best_bid", "best_ask", "neg_risk", "liquidity", "volume24hr"]
ECOLS = ["market_id", "fee_type", "fee_category", "series_slugs", "clob_rewards", "order_price_min_tick_size", "volume_num", "fees_enabled", "fee_schedule", "created_at",
         "accepting_orders", "uma_resolution_statuses", "event_comment_count", "event_volume", "future_trap_column"]
FEE_ON = '{"exponent":1,"rate":0.05,"rebateRate":0.25,"takerOnly":true}'
FEE_0 = '{"exponent":1,"rate":0,"rebateRate":0,"takerOnly":true}'
CAT = "politics"
CRE = "2026-05-01T00:00:00Z"


def mk(mid, ev, bid, ask, vol=0.0, nr=False, rw="", fs=FEE_ON, fe="1", created=CRE, acc="true", uma="", ecc="", evol="", t=None):
    rec = (t or T0).strftime("%Y-%m-%dT%H:%M:%SZ")
    return ({"market_id": mid, "event_id": ev, "received_utc": rec, "closed": "false", "active": "true", "binary": "true", "best_bid": f"{bid:.4f}", "best_ask": f"{ask:.4f}",
             "neg_risk": str(nr).lower(), "liquidity": "1000", "volume24hr": "777"},
            {"market_id": mid, "fee_type": "", "fee_category": CAT, "series_slugs": "", "clob_rewards": rw, "order_price_min_tick_size": "0.01", "volume_num": str(vol),
             "fees_enabled": fe, "fee_schedule": fs, "created_at": created, "accepting_orders": acc, "uma_resolution_statuses": uma, "event_comment_count": str(ecc),
             "event_volume": str(evol), "future_trap_column": "NEVER"})


def sp(mid, ev, mid_p, spread, **kw):
    return mk(mid, ev, mid_p - spread / 2, mid_p + spread / 2, **kw)


def write_cap(root: Path, k: int, items, hours=None):
    t = T0 + timedelta(hours=2 * k if hours is None else hours)
    d = root / f"cap{k:03d}"
    d.mkdir(parents=True)
    (d / "manifest.json").write_text(json.dumps({"state": "complete", "started_utc": t.strftime("%Y-%m-%dT%H:%M:%SZ")}))
    for name, cols, idx in (("rows.csv.gz", RCOLS, 0), ("rows_ext.csv.gz", ECOLS, 1)):
        with gzip.open(d / name, "wt", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for it in items:
                w.writerow(it[idx])
    return d


def span(days=1):
    return "2026-10-16T00:00:00Z", (T0 - timedelta(minutes=31) + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def tot(res, section, key):
    v = res[section].get(key)
    return v["total"] if v else 0


def test_widenings_narrowings_cells_and_coverage_proxy(tmp_path):
    k0, k1 = [], []
    for i in range(20):  # fee-on unrewarded widening units (post-03-30) fill the cell
        k0.append(sp(f"N{i}", f"n{i}", 0.5, 0.01))
        k1.append(sp(f"N{i}", f"n{i}", 0.5, 0.03))
    for name, s0, s1 in (("A", 0.03, 0.01), ("B", 0.01, 0.03), ("C", 0.01, 0.03), ("D", 0.01, 0.015)):  # A narrows, B and C widen, D within 2 ticks
        k0.append(sp(name, "e" + name, 0.5, s0, fs=FEE_0))
        k1.append(sp(name, "e" + name, 0.5, s1, fs=FEE_0))
    k0.append(sp("R", "eR", 0.5, 0.01, rw="x", fs=FEE_0))
    k1.append(sp("R", "eR", 0.5, 0.05, rw="x", fs=FEE_0))  # rewarded fee-free widening: another cell
    write_cap(tmp_path, 0, k0)
    write_cap(tmp_path, 1, k1)
    res = m.run_map([tmp_path], *span())
    c, ch = "nonsports_excrypto", "change_counts"
    assert tot(res, ch, f"ch252/widenings/fee_free/unrewarded/{c}") == 2
    assert tot(res, ch, f"ch252/narrowings/fee_free/unrewarded/{c}") == 1
    assert tot(res, ch, f"ch252/units_complete/fee_free/unrewarded/{c}") == 4
    assert tot(res, ch, f"ch252/widenings/fee_free/rewarded/{c}") == 1
    assert tot(res, ch, f"ch252/widenings/fee_on/unrewarded/{c}") == 20
    assert tot(res, ch, f"ch252/widenings_age/fee_free/unrewarded/{c}/post_0330") == 2
    assert res["shares"][f"ch252/widening_share/fee_free/unrewarded/{c}"] == 0.5
    assert res["shares"][f"ch252/fee_free_unrewarded_cell_coverage_proxy/{c}"] == 1.0
    h = res["headline"]["ch252_fee_free_unrewarded_widenings_per_capture_nonsports_excrypto"]
    assert h["n_captures"] == 1 and h["median"] == 2 and h["min"] == 2 and h["mean"] == 2
    assert res["headline"]["spec_lines_reported_not_applied"]["ch255_traded_first_of_day_flips_per_capture_line"] == 690


def test_creation_batches_cross_event_corr_and_unavailable(tmp_path):
    batch = [("B1", "E1", "2026-05-01T00:00:00Z"), ("B2", "E1", "2026-05-01T00:00:30Z"), ("B3", "E2", "2026-05-01T00:01:00Z"), ("B4", "E3", "2026-05-01T00:01:40Z")]
    for k in range(2):
        items = []
        for i, (mid, ev, cr) in enumerate(batch):
            items.append(sp(mid, ev, 0.5, 0.01 if k == 0 else 0.02 + 0.01 * i, created=cr))
        for j in range(12):  # background singles created days apart
            items.append(sp(f"S{j}", f"s{j}", 0.5, 0.01, created=f"2026-06-{j + 1:02d}T00:00:00Z"))
        items += [sp("SAME1", "X", 0.5, 0.01, created="2026-09-01T00:00:00Z"), sp("SAME2", "X", 0.5, 0.01, created="2026-09-01T00:00:10Z"), sp("SAME3", "X", 0.5, 0.01, created="2026-09-01T00:00:20Z")]
        items += [sp("U1", "U", 0.5, 0.01, created="2026-08-01T00:00:00Z"), sp("U2", "V", 0.5, 0.01, created="2026-08-01T00:00:50Z"), sp("U3", "W", 0.5, 0.01, created="2026-08-01T00:01:10Z")]
        if k == 1:  # a cross-event batch where one of three members is one-sided at k: 2/3 >= 60% still available; two one-sided: unavailable
            items[-1] = mk("U3", "W", 0.0, 0.5, created="2026-08-01T00:01:10Z")
            items[-2] = mk("U2", "V", 0.0, 0.5, created="2026-08-01T00:00:50Z")
        write_cap(tmp_path, k, items)
    res = m.run_map([tmp_path], *span())
    ch, lv = "change_counts", "level_counts"
    assert tot(res, lv, "ch253/batches_cross_event/4-5") == 2
    assert tot(res, lv, "ch253/batches_cross_event/3") == 2  # U1-U3 at both captures
    assert tot(res, lv, "ch253/batches_ge3_single_event") == 2  # SAME1-3
    assert tot(res, ch, "ch253/batch_captures_unavailable_under_60pct_complete") == 1  # U batch at k = 1
    assert tot(res, ch, "ch253/primary_units") == 4  # the four batch units only
    assert res["correlations"]["ch253/same_slot_corr_own_vs_mates_mean_innovation"]["n"] == 4
    assert res["correlations"]["ch253/same_slot_corr_own_vs_mates_mean_innovation"]["corr"] is not None
    assert tot(res, ch, "ch253/primary_units_pseudo_batch_covered") + tot(res, ch, "ch253/primary_units_pseudo_batch_not_covered") == 4
    assert res["shares"]["ch253/eligible_rows_in_cross_event_batch_ge3_share"] > 0
    assert res["ch253_batch_days"][0]["batches_ge_24_units"] == 0 and res["ch253_batch_days"][0]["batches_with_a_unit"] == 1


def test_first_of_day_flips_trade_class_visibility_reflip_and_two_member(tmp_path):
    def cap(k, a, b, c, va, vb, two):
        t = T0 + timedelta(hours=2 * k)
        it = [sp("L0", "RACE", a, 0.01, nr=True, vol=va, evol=1000, t=t), sp("L1", "RACE", b, 0.01, nr=True, vol=vb, evol=1000, t=t), sp("L2", "RACE", c, 0.01, nr=True, vol=1, evol=1000, t=t)]
        it += [sp("T0", "TWO", two[0], 0.01, nr=True, vol=1, t=t), sp("T1", "TWO", two[1], 0.01, nr=True, vol=1 + k * 3, t=t)]
        return it

    write_cap(tmp_path, 0, cap(0, 0.5, 0.3, 0.2, 1, 1, (0.55, 0.45)))
    write_cap(tmp_path, 1, cap(1, 0.3, 0.5, 0.2, 1, 5, (0.45, 0.55)))  # L1 takes the lead with a print; TWO flips with a print
    write_cap(tmp_path, 2, cap(2, 0.5, 0.3, 0.2, 9, 5, (0.55, 0.45)))  # back again the same UTC day: a re-flip
    res = m.run_map([tmp_path], *span())
    c, ch = "nonsports_excrypto", "change_counts"
    assert tot(res, ch, f"ch255/flips_first_of_day/traded/3-5/top200/{c}") == 1
    assert tot(res, ch, f"ch255/flips_first_of_day_total/traded/{c}") == 2  # RACE and TWO
    assert tot(res, ch, f"ch255/flips_first_of_day_two_member_held_out/traded/{c}") == 1
    assert tot(res, ch, f"ch255/flips_first_of_day_ex_two_member/traded/{c}") == 1
    assert tot(res, ch, f"ch255/reflips/{c}") == 2
    assert res["distinct_events_over_span"][f"ch255/flip_events/{c}"] == 2
    assert res["headline"]["ch255_traded_first_of_day_flips_per_capture_nonsports_excrypto"]["total"] == 2
    assert 0 < res["shares"]["ch255/reflip_share_of_to_runner_up_flips"] < 1


def test_collapses_comments_halts_and_fee_per_stake(tmp_path):
    for k in range(4):
        t = T0 + timedelta(hours=2 * k)
        it = [sp("F", "ef", 0.90, 0.01, vol=100, uma="proposed" if k == 1 else "", t=t)] if k == 0 else [sp("F", "ef", 0.10, 0.01, vol=100, uma="proposed", t=t)]
        if k == 0:
            it.append(sp("GONE", "eg", 0.92, 0.01, t=t))  # a favourite that is absent from the open rows afterwards
        for i, (c0, c1, v0, v1) in enumerate(((3, 10, 100, 200), (0, 0, 50, 50), (1, 2, 10, 30), (4, 5, 20, 90))):
            it.append(sp(f"C{i}", f"ec{i}", 0.5, 0.01, ecc=(c0 if k == 0 else c1), evol=(v0 if k == 0 else v1), t=t))
        it.append(sp("H", "eh", (0.5, 0.5, 0.6, 0.7)[k], 0.01, acc="false" if k in (1, 2) else "true", t=t))  # observed halt start at k = 1, reopens at 3
        it.append(sp("G", "eg2", 0.5, 0.01, acc="false" if k < 3 else "true", t=t))  # halted from the first capture: left-censored
        write_cap(tmp_path, k, it)
    res = m.run_map([tmp_path], *span())
    c, ch = "nonsports_excrypto", "change_counts"
    assert tot(res, ch, f"ch254/collapses/crash_uma_proposed_at_k/{c}") == 1
    assert res["quantiles"][f"ch254/collapse_volume_num/{c}"]["n"] == 1
    assert res["category_days_with_a_collapse"] == {c: 1}
    assert tot(res, ch, f"ch254/favourites_km1_absent_from_open_rows_at_k/{c}") == 1
    assert res["shares"]["ch256/comment_field_presence_share_eligible_rows"] > 0
    assert tot(res, ch, "ch256/comment_bursts_ge5") == 1
    assert res["shares"]["ch256/comment_change_share_of_event_captures"] == 0.25  # 3 of 12 event-captures changed (all at the first transition)
    assert res["correlations"]["ch256/comment_change_vs_event_volume_change"]["n"] == 12
    assert res["quantiles"][f"ch257/halt_length_captures/{c}"]["n"] == 1 and res["quantiles"][f"ch257/halt_length_captures/{c}"]["q50"] == 2.0
    assert tot(res, ch, f"ch257/halt_reopened_left_censored/{c}") == 1
    assert tot(res, ch, f"ch257/halt_reopened_observed_start/{c}") == 1
    mv = res["quantiles"][f"ch257/reopen_abs_move_across_reopen_capture/{c}"]
    assert mv["n"] == 2 and abs(mv["q95"] - 0.1) < 1e-6 and abs(mv["q05"]) < 1e-6  # H: 0.6 -> 0.7; G: 0.5 -> 0.5
    assert tot(res, "level_counts", f"ch257/halted_rows/{c}") == 2 + 3  # H at k = 1, 2 and G at k = 0, 1, 2
    assert tot(res, "level_counts", f"ch260/fee_per_stake_ge_0.02/unrewarded/{c}") > 0


def test_inputs_hashed_not_mapped_and_code_hashes(tmp_path):
    write_cap(tmp_path, 0, [sp("A", "a", 0.5, 0.01)])
    res = m.run_map([tmp_path], *span())
    assert len(res["inputs"]) == 3 and all(len(i["sha256"]) == 64 and i["bytes"] > 0 for i in res["inputs"])
    assert set(res["code_sha256"]) == {"population_map_ch261.py", "run_ch261_map.py"}
    for key in ("k_plus_1_targets", "ch258_stress_slots", "ch259_prediction_dispersion", "ch260_res7d_census", "liquidity_tier", "ch254_vanished_at_k_plus_1"):
        assert key in res["not_mapped"] and res["not_mapped"][key].startswith(("unavailable", "partial"))
    assert "future_trap_column" not in m.EXT_COLS and "future_trap_column" not in m.ROW_COLS


def test_no_capture_k_plus_one_is_read_or_used(tmp_path, monkeypatch):
    a, bdir = tmp_path / "a", tmp_path / "b"
    for root, last in ((a, [sp("A", "E", 0.9, 0.2, vol=999, uma="proposed", acc="false"), sp("B", "E", 0.1, 0.2, nr=True)]), (bdir, [sp("A", "E", 0.5, 0.01)])):
        write_cap(root, 0, [sp("A", "E", 0.5, 0.01), sp("B", "E", 0.5, 0.01, nr=True)])
        write_cap(root, 1, [sp("A", "E", 0.5, 0.03), sp("B", "E", 0.5, 0.03, nr=True)])
        write_cap(root, 2, last)
    end = (T0 + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    seen = []
    orig_r, orig_e = c251.read_rows, m.read_ext
    monkeypatch.setattr(c251, "read_rows", lambda p: (seen.append(p.parent.name), orig_r(p))[1])
    monkeypatch.setattr(m, "read_ext", lambda p, keep: (seen.append(p.parent.name), orig_e(p, keep))[1])
    ra, rb = m.run_map([a], "2026-10-16T00:00:00Z", end), m.run_map([bdir], "2026-10-16T00:00:00Z", end)
    assert set(seen) == {"cap000", "cap001"}
    keep = ("level_counts", "change_counts", "distinct_events_over_span", "quantiles", "correlations", "shares", "headline", "ch253_batch_days")
    assert {k: ra[k] for k in keep} == {k: rb[k] for k in keep}
    order = []
    orig_feed = m.Mapper.feed
    monkeypatch.setattr(m.Mapper, "feed", lambda self, t, rows, ext: (order.append(t), orig_feed(self, t, rows, ext))[1])
    m.run_map([a], "2026-10-16T00:00:00Z", (T0 + timedelta(hours=7)).strftime("%Y-%m-%dT%H:%M:%SZ"))
    assert order == sorted(order) and len(order) == 3


def test_gap_means_no_previous_capture(tmp_path):
    write_cap(tmp_path, 0, [sp("A", "a", 0.5, 0.01)])
    write_cap(tmp_path, 1, [sp("A", "a", 0.5, 0.05)], hours=6)
    res = m.run_map([tmp_path], *span())
    assert res["change_counts"] == {} and res["notes"]["previous_capture_gap_too_large"] == 1


def test_runner_guards_refuse_paths_overwrite_and_caps(tmp_path, monkeypatch):
    snap = tmp_path / "research_lab" / "snapshots"
    write_cap(snap, 0, [sp("A", "a", 0.5, 0.01)])
    out = tmp_path / "research_lab" / "o" / "m.json"
    args = ["--snapshot-root", str(snap), "--start-utc", "2026-10-16T00:00:00Z", "--end-utc", "2026-10-17T00:00:00Z", "--out", str(out)]
    assert runner.main(args) == 0 and out.exists()
    doc = json.loads(out.read_text())
    assert doc["version"] == m.VERSION and doc["span"]["mode"] == "explicit"
    assert runner.main(args) == 1
    bad_root = tmp_path / "elsewhere"
    write_cap(bad_root, 0, [sp("A", "a", 0.5, 0.01)])
    assert runner.main([*args[:1], str(bad_root), *args[2:-1], str(tmp_path / "research_lab" / "o" / "x.json")]) == 2
    assert runner.main([*args[:-1], str(tmp_path / "outside" / "x.json")]) == 2
    out2 = tmp_path / "research_lab" / "o" / "m2.json"
    monkeypatch.setattr(runner, "_above_cap", lambda gb: True)
    assert runner.main([*args[:-1], str(out2), "--data-dumps-cap-gb", "40"]) == 75
    assert not out2.exists()
    monkeypatch.setattr(runner, "_above_cap", lambda gb: False)
    assert runner.main([*args[:-1], str(out2), "--min-free-gb", "1e9"]) == 75


def test_last_days_span_is_declared(tmp_path):
    snap = tmp_path / "research_lab" / "snapshots"
    write_cap(snap, 0, [sp("A", "a", 0.5, 0.01)])
    write_cap(snap, 1, [sp("A", "a", 0.5, 0.02)])
    out = tmp_path / "research_lab" / "o" / "m.json"
    assert runner.main(["--snapshot-root", str(snap), "--last-days", "14", "--out", str(out)]) == 0
    doc = json.loads(out.read_text())
    assert doc["span"]["mode"] == "last_days=14" and doc["captures"]["covered"] == 2 and doc["span"]["end_utc"] > doc["span"]["start_utc"]
