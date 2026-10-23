# ruff: noqa: E501
"""CH251 population map: synthetic captures only (no data-dumps reads)."""

from __future__ import annotations

import csv
import gzip
import importlib.util
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from astrolabe.research_lab import population_map_ch251 as m

_P = Path(__file__).resolve().parents[2] / "scripts" / "run_ch251_map.py"
_spec = importlib.util.spec_from_file_location("run_ch251_map_under_test", _P)
runner = importlib.util.module_from_spec(_spec)
sys.modules["run_ch251_map_under_test"] = runner
_spec.loader.exec_module(runner)

T0 = datetime(2026, 10, 16, 0, 31, tzinfo=UTC)
RCOLS = ["market_id", "event_id", "received_utc", "closed", "active", "binary", "best_bid", "best_ask", "neg_risk", "liquidity", "volume24hr"]
ECOLS = ["market_id", "fee_type", "fee_category", "series_slugs", "clob_rewards", "order_price_min_tick_size", "volume_num", "fees_enabled", "fee_schedule", "created_at"]
FEE_ON = '{"exponent":1,"rate":0.05,"rebateRate":0.25,"takerOnly":true}'
FEE_0 = '{"exponent":1,"rate":0,"rebateRate":0,"takerOnly":true}'
CAT = "politics"


def mk(mid, ev, mid_p, vol=0.0, half=0.005, nr=True, rw="", fs=FEE_ON, fe="1", created="2026-05-01T00:00:00Z", rec_off=0, liq=1000.0, bid=None, ask=None, t=None):
    b_, a_ = (mid_p - half, mid_p + half) if bid is None else (bid, ask)
    rec = ((t or T0) + timedelta(seconds=rec_off)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return ({"market_id": mid, "event_id": ev, "received_utc": rec, "closed": "false", "active": "true", "binary": "true", "best_bid": f"{b_:.4f}", "best_ask": f"{a_:.4f}",
             "neg_risk": str(nr).lower(), "liquidity": str(liq), "volume24hr": "777"},
            {"market_id": mid, "fee_type": "", "fee_category": CAT, "series_slugs": "", "clob_rewards": rw, "order_price_min_tick_size": "0.01", "volume_num": str(vol),
             "fees_enabled": fe, "fee_schedule": fs, "created_at": created})


def write_cap(root: Path, k: int, items, hours=None):
    t = T0 + timedelta(hours=2 * k if hours is None else hours)
    d = root / f"cap{k:03d}"
    d.mkdir(parents=True)
    (d / "manifest.json").write_text(json.dumps({"state": "complete", "started_utc": t.strftime("%Y-%m-%dT%H:%M:%SZ")}))
    for name, cols, idx in (("rows.csv.gz", RCOLS, 0), ("rows_ext.csv.gz", ECOLS, 1)):
        with gzip.open(d / name, "wt", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            for it in items:
                w.writerow(it[idx])
    return d


def span(days=1):
    return "2026-10-16T00:00:00Z", (T0 - timedelta(minutes=31) + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def tot(res, section, key):
    v = res[section].get(key)
    return v["total"] if v else 0


def pair(k, a_mid, b_mid, half_a=0.005, half_b=0.005, rw_a="", rw_b="", vol_a=0.0, vol_b=0.0, off_b=0, ev="E", tt=None):
    t = tt or (T0 + timedelta(hours=2 * k))
    return [mk("A", ev, a_mid, vol=vol_a, half=half_a, rw=rw_a, t=t), mk("B", ev, b_mid, vol=vol_b, half=half_b, rw=rw_b, rec_off=off_b, t=t)]


def test_two_member_complete_pairs_span_gaps_and_shares(tmp_path):
    # pair P1 ok; pair P2's B receipt is 300 s off at k (excluded by span); P3 has B one-sided at k - 1 (not a complete pair)
    for k in range(2):
        t = T0 + timedelta(hours=2 * k)
        items = pair(k, 0.60, 0.40, half_a=0.01 * (k + 1), half_b=0.005, ev="P1", tt=t)
        items += [mk("C", "P2", 0.5, t=t), mk("D", "P2", 0.5, rec_off=300 * k, t=t)]
        items += [mk("F", "P3", 0.5, t=t), mk("G", "P3", 0.5, t=t, bid=(0.0 if k == 0 else 0.495), ask=0.505)]
        write_cap(tmp_path, k, items)
    res = m.run_map([tmp_path], *span())
    s = "nonsports_excrypto/uu"
    assert tot(res, "level_counts", f"ch245/two_member_events/{s}") == 6  # 3 events x 2 captures
    assert tot(res, "level_counts", f"ch245/two_member_complete_at_k/{s}") == 5  # P3 not complete at k = 0
    assert tot(res, "change_counts", f"ch245/complete_pairs_k_km1/{s}") == 2  # P1, P2 (P3 not complete at k - 1)
    assert tot(res, "change_counts", f"ch245/complete_at_k_not_complete_pair_km1/{s}") == 1
    assert tot(res, "change_counts", f"ch245/span_excluded_at_k/{s}") == 1
    assert tot(res, "change_counts", f"ch245/pairs_span_retained/{s}") == 1
    assert tot(res, "change_counts", f"ch245/member_units_retained/{s}") == 2
    assert res["shares"][f"ch245/span_retention_share/{s}"] == 0.5
    # P1: spreads at k - 1 are 0.02 (A) and 0.01 (B) -> one thin, one dense unit; gaps at k: g_A = ask_A + bid_B - 1, g_B = bid_A + ask_B - 1
    assert tot(res, "change_counts", f"ch245/thin_units/{s}") == 1 and tot(res, "change_counts", f"ch245/dense_units/{s}") == 1
    q = res["quantiles"][f"ch245/mirror_gap_g/{s}"]
    assert q["n"] == 2 and abs(q["q05"] - (-0.015)) < 1e-6 and abs(q["q95"] - 0.015) < 1e-6


def test_sym_and_innovation_corr(tmp_path):
    # the two books widen together in the same slot on a symmetric pair
    for k, h in enumerate((0.005, 0.005, 0.01, 0.01)):
        write_cap(tmp_path, k, pair(k, 0.5, 0.5, half_a=h, half_b=h))
    res = m.run_map([tmp_path], *span())
    s = "nonsports_excrypto/uu"
    assert tot(res, "change_counts", f"ch245/sym_units/{s}") == 6  # 3 transitions x 2 units
    assert res["shares"][f"ch245/sym_share/{s}"] == 1.0
    assert tot(res, "change_counts", f"ch245/pairs_both_nonzero_same_sign/{s}") == 1
    assert tot(res, "change_counts", f"ch245/pairs_both_innovation_zero/{s}") == 2
    assert res["correlations"][f"ch245/spread_innovation_corr/{s}"]["n"] == 6


def test_ch248_who_printed(tmp_path):
    k0 = pair(0, 0.50, 0.50, vol_a=10, vol_b=10)
    k1 = pair(1, 0.55, 0.45, vol_a=10, vol_b=25)  # A moved +0.05 with only the twin printing; B moved -0.05 with its own print
    write_cap(tmp_path, 0, k0)
    write_cap(tmp_path, 1, k1)
    res = m.run_map([tmp_path], *span())
    c = "nonsports_excrypto"
    assert tot(res, "change_counts", f"ch248/movers/twin_printed/unrewarded/{c}") == 1
    assert tot(res, "change_counts", f"ch248/movers/own_printed/unrewarded/{c}") == 1
    assert tot(res, "change_counts", f"ch248/movers_total/unrewarded/{c}") == 2


def test_ch248_unknown_volume(tmp_path):
    write_cap(tmp_path, 0, pair(0, 0.50, 0.50, vol_a=float("nan"), vol_b=10))
    write_cap(tmp_path, 1, pair(1, 0.55, 0.50, vol_a=5, vol_b=10))
    res = m.run_map([tmp_path], *span())
    assert tot(res, "change_counts", "ch248/movers/unknown/unrewarded/nonsports_excrypto") == 1


def _ladder(k, mids, rws, moved=None):
    items = []
    for i, (p, rw) in enumerate(zip(mids, rws, strict=True)):
        items.append(mk(f"L{i}", "LAD", p + (moved or {}).get(i, 0.0) * k, rw=rw, liq=100.0 * (i + 1) * (5 if rw else 1)))
    return items


def test_mixed_ladder_counts_completeness_shock_and_corr(tmp_path):
    rws = ["x", "x", "", ""]  # two rewarded, two unrewarded -> mixed; plus a one-sided member in an all-unrewarded ladder elsewhere
    for k in range(2):
        items = _ladder(k, [0.4, 0.3, 0.2, 0.1], rws, moved={0: 0.03})  # member 0 moves 3 ticks at k = 1
        items += [mk("X0", "ALLU", 0.5, rw=""), mk("X1", "ALLU", 0.3, rw=""), mk("X2", "ALLU", 0.2, rw="", bid=0.0, ask=0.2)]
        write_cap(tmp_path, k, items)
    res = m.run_map([tmp_path], *span())
    c = "nonsports_excrypto"
    assert tot(res, "level_counts", f"ch244/ladders/mixed/3-5/{c}") == 2
    assert tot(res, "level_counts", f"ch244/ladders/all_unrewarded/3-5/{c}") == 2
    assert tot(res, "level_counts", f"ch244/ladders_complete/all_unrewarded/3-5/{c}") == 0
    assert tot(res, "level_counts", f"ch244/mixed_members/rewarded/3-5/{c}") == 4
    assert tot(res, "level_counts", f"ch244/mixed_members/unrewarded/3-5/{c}") == 4
    assert tot(res, "change_counts", f"ch244/complete_pairs/mixed/3-5/{c}") == 1
    # member 0 moved 0.03 >= 2 x 0.01: its three siblings are shocked, member 0 itself is not
    assert tot(res, "change_counts", f"ch244/shock_units/mixed/rewarded/{c}") == 1
    assert tot(res, "change_counts", f"ch244/shock_units/mixed/unrewarded/{c}") == 2
    assert tot(res, "change_counts", f"ch244/units/mixed/unrewarded/{c}") == 2
    assert res["shares"][f"ch244/shock_share/mixed/unrewarded/{c}"] == 1.0
    # unrewarded members have lower liquidity: negative within-event correlation of unrew with log liquidity
    assert res["correlations"][f"ch244/status_liquidity_corr_within_event/3-10/{c}"]["corr"] < -0.5
    assert res["distinct_events_over_span"][f"ch244/mixed/{c}"] == 1


def test_fee_sources_cells_and_coverage_proxy(tmp_path):
    k0, k1 = [], []
    for i in range(22):  # fee-on movers (traded), rewarded
        k0.append(mk(f"N{i}", f"n{i}", 0.30, vol=1, nr=False, rw="x"))
        k1.append(mk(f"N{i}", f"n{i}", 0.35, vol=2, nr=False, rw="x"))
    for name, kw in (("F0", dict(fs=FEE_0)), ("F1", dict(fe="0", fs="")), ("F2", dict(fs=FEE_0, created="2026-02-01T00:00:00Z"))):
        k0.append(mk(name, "e" + name, 0.30, vol=1, nr=False, **kw))
        k1.append(mk(name, "e" + name, 0.35, vol=1, nr=False, **kw))  # quote-only movers, fee-free
    k0.append(mk("T", "eT", 0.30, vol=1, nr=False, fs=FEE_0))
    k1.append(mk("T", "eT", 0.36, vol=3, nr=False, fs=FEE_0))  # a traded fee-free mover
    k0.append(mk("EDGE", "eEdge", 0.02, vol=1, nr=False))
    k1.append(mk("EDGE", "eEdge", 0.05, vol=2, nr=False))  # p_{k-1} outside [0.04, 0.96]: not a CH243 / CH250 mover
    write_cap(tmp_path, 0, k0)
    write_cap(tmp_path, 1, k1)
    res = m.run_map([tmp_path], *span())
    c = "nonsports_excrypto"
    ch = "change_counts"
    assert tot(res, ch, f"ch250/movers_traded/fee_on/rewarded/{c}") == 22
    assert tot(res, ch, f"ch250/movers_quote_only/fee_free/unrewarded/{c}") == 3
    assert tot(res, ch, f"ch250/movers_traded/fee_free/unrewarded/{c}") == 1
    assert tot(res, ch, f"ch243/movers_quote_only/rate_zero/post_0330/{c}") == 1
    assert tot(res, ch, f"ch243/movers_quote_only/rate_zero/pre_0330/{c}") == 1  # F2, created 2026-02
    assert tot(res, ch, f"ch243/movers_quote_only/rate_zero/age_na/{c}") == 0
    assert tot(res, ch, f"ch243/movers_quote_only/flag_off/post_0330/{c}") == 1
    assert tot(res, ch, f"ch243/fee_free_movers_classed/{c}") == 4
    # the proxy: fee-on movers (22, all post_0330) cover only the post_0330 cell
    assert tot(res, ch, f"ch243/fee_free_movers_in_covered_cell_proxy/{c}") == 3
    assert tot(res, "level_counts", f"ch250/rows_open_binary/fee_free/unrewarded/{c}") == 2 * 4  # F0, F1, F2, T at two captures
    assert res["shares"][f"ch250/fee_free_row_share_both_rw/{c}"] > 0


def test_inputs_hashed_not_mapped_and_code_hashes(tmp_path):
    write_cap(tmp_path, 0, pair(0, 0.5, 0.5))
    res = m.run_map([tmp_path], *span())
    assert len(res["inputs"]) == 3 and all(len(i["sha256"]) == 64 and i["bytes"] > 0 for i in res["inputs"])
    assert set(res["code_sha256"]) == {"population_map_ch251.py", "run_ch251_map.py"}
    assert "ch246_duplicate_pairs" in res["not_mapped"] and "ch242_split_resolutions" in res["not_mapped"]


def test_no_capture_k_plus_one_is_read_or_used(tmp_path, monkeypatch):
    a, bdir = tmp_path / "a", tmp_path / "b"
    for root, last in ((a, pair(2, 0.9, 0.1, vol_a=999, vol_b=999)), (bdir, pair(2, 0.5, 0.5))):
        write_cap(root, 0, pair(0, 0.50, 0.50))
        write_cap(root, 1, pair(1, 0.55, 0.45))
        write_cap(root, 2, last)
    end = (T0 + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")  # window = captures 0 and 1 only
    seen = []
    orig = m.read_rows
    monkeypatch.setattr(m, "read_rows", lambda p: (seen.append(p.parent.name), orig(p))[1])
    ra, rb = m.run_map([a], "2026-10-16T00:00:00Z", end), m.run_map([bdir], "2026-10-16T00:00:00Z", end)
    assert set(seen) == {"cap000", "cap001"}  # the third capture is never opened
    keep = ("level_counts", "change_counts", "distinct_events_over_span", "quantiles", "correlations", "shares")
    assert {k: ra[k] for k in keep} == {k: rb[k] for k in keep}
    # inside the window, capture k's counts do not depend on k + 1 either: feed order is strictly k - 1 then k
    order = []
    orig_feed = m.Mapper.feed
    monkeypatch.setattr(m.Mapper, "feed", lambda self, t, rows, ext: (order.append(t), orig_feed(self, t, rows, ext))[1])
    m.run_map([a], "2026-10-16T00:00:00Z", (T0 + timedelta(hours=7)).strftime("%Y-%m-%dT%H:%M:%SZ"))
    assert order == sorted(order) and len(order) == 3


def test_gap_means_no_previous_capture(tmp_path):
    write_cap(tmp_path, 0, pair(0, 0.5, 0.5))
    write_cap(tmp_path, 1, pair(1, 0.6, 0.4), hours=6)
    res = m.run_map([tmp_path], *span())
    assert res["change_counts"] == {} and res["notes"]["previous_capture_gap_too_large"] == 1


def test_runner_refuses_overwrite_and_caps(tmp_path, monkeypatch):
    write_cap(tmp_path / "snap", 0, pair(0, 0.5, 0.5))
    out = tmp_path / "o" / "m.json"
    args = ["--snapshot-root", str(tmp_path / "snap"), "--start-utc", "2026-10-16T00:00:00Z", "--end-utc", "2026-10-17T00:00:00Z", "--out", str(out)]
    assert runner.main(args) == 0 and out.exists()
    assert json.loads(out.read_text())["version"] == m.VERSION
    assert runner.main(args) == 1
    out2 = tmp_path / "o" / "m2.json"
    monkeypatch.setattr(runner, "_above_cap", lambda gb: True)
    assert runner.main([*args[:-1], str(out2), "--data-dumps-cap-gb", "0.0001"]) == 75
    assert not out2.exists()
