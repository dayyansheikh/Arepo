# ruff: noqa: E501
"""CH240 boundary map: synthetic captures only (no data-dumps reads)."""

from __future__ import annotations

import csv
import gzip
import importlib.util
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from astrolabe.research_lab import boundary_map_ch240 as m

_P = Path(__file__).resolve().parents[2] / "scripts" / "run_ch240_map.py"
_spec = importlib.util.spec_from_file_location("run_ch240_map_under_test", _P)
runner = importlib.util.module_from_spec(_spec)
sys.modules["run_ch240_map_under_test"] = runner
_spec.loader.exec_module(runner)

T0 = datetime(2026, 10, 16, 0, 31, tzinfo=UTC)
RCOLS = ["market_id", "event_id", "received_utc", "closed", "active", "binary", "best_bid", "best_ask", "neg_risk", "neg_risk_market_id", "volume24hr"]
ECOLS = ["market_id", "fee_type", "fee_category", "series_slugs", "clob_rewards", "order_price_min_tick_size", "volume_num"]


def mk(mid, ev, mid_p, vol=0.0, half=0.005, nr=False, two=True, rw="", cat="politics", tick=0.01):
    bid, ask = (mid_p - half, mid_p + half) if two else (0.0, mid_p + half)
    return ({"market_id": mid, "event_id": ev, "received_utc": "x", "closed": "false", "active": "true", "binary": "true", "best_bid": f"{bid:.4f}",
             "best_ask": f"{ask:.4f}", "neg_risk": str(nr).lower(), "neg_risk_market_id": "", "volume24hr": "777"},
            {"market_id": mid, "fee_type": "", "fee_category": cat, "series_slugs": "", "clob_rewards": rw, "order_price_min_tick_size": str(tick), "volume_num": str(vol)})


def write_cap(root: Path, k: int, items, hours: float | None = None, with_ext=True) -> Path:
    t = T0 + timedelta(hours=2 * k if hours is None else hours)
    d = root / f"cap{k:03d}"
    d.mkdir(parents=True)
    (d / "manifest.json").write_text(json.dumps({"state": "complete", "started_utc": t.strftime("%Y-%m-%dT%H:%M:%SZ")}))
    for name, cols, idx in (("rows.csv.gz", RCOLS, 0), ("rows_ext.csv.gz", ECOLS, 1)):
        if idx == 1 and not with_ext:
            continue
        with gzip.open(d / name, "wt", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            for it in items:
                w.writerow(it[idx])
    return d


def span(days=1):
    return "2026-10-16T00:00:00Z", (T0 - timedelta(minutes=31) + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def total(res, section, prefix):
    return sum(v["total"] for k, v in res[section].items() if k.startswith(prefix))


def test_crossing_direction_and_ticks():
    assert m.crossing(0.12, 0.08, 0.10) == "outward"
    assert m.crossing(0.08, 0.12, 0.10) == "inward"
    assert m.crossing(0.88, 0.92, 0.90) == "outward"
    assert m.crossing(0.92, 0.88, 0.90) == "inward"
    assert m.crossing(0.2, 0.3, 0.10) is None
    assert m.crossing(float("nan"), 0.3, 0.10) is None


def test_crossing_recrossing_and_tick_coincidence(tmp_path):
    # market A: 0.105 -> 0.095 (single 0.01 tick: coincident outward) -> 0.105 (inward recross) -> 0.05 (outward? no: 0.10 already crossed)
    # market B: 0.20 -> 0.08 (non coincident outward first crossing, also 0.04 not crossed)
    path = [(0.105, 0.20), (0.095, 0.08), (0.105, 0.08)]
    for k, (a, bb) in enumerate(path):
        write_cap(tmp_path, k, [mk("A", "e1", a), mk("B", "e2", bb)])
    res = m.run_map([tmp_path], *span())
    c = res["change_counts"]
    assert c["ch232/first_crossings/b0.10/outward/nonsports_excrypto/unrewarded"]["total"] == 2
    assert c["ch232/first_crossings_tick_coincident/b0.10/outward/nonsports_excrypto/unrewarded"]["total"] == 1
    assert c["ch232/first_crossings_ex_tick/b0.10/outward/nonsports_excrypto/unrewarded"]["total"] == 1
    assert c["ch232/recrossings/b0.10/inward/nonsports_excrypto/unrewarded"]["total"] == 1
    assert "ch232/first_crossings/b0.10/inward/nonsports_excrypto/unrewarded" not in c
    # re-crossing share: two market-days with a crossing (A and B), one of them (A) with >= 2
    assert res["shares"]["ch232/recross_share/b0.10/nonsports_excrypto/unrewarded"] == pytest.approx(0.5)
    assert res["distinct_events_over_span"]["ch232/b0.10/nonsports_excrypto/unrewarded"] == 2


def test_reward_and_category_split(tmp_path):
    items0 = [mk("R", "e1", 0.12, rw='[{"rewardsDailyRate": 5}]'), mk("S", "e2", 0.12, cat="sports"), mk("C", "e3", 0.12, cat="crypto")]
    items1 = [mk("R", "e1", 0.08, rw='[{"rewardsDailyRate": 5}]'), mk("S", "e2", 0.08, cat="sports"), mk("C", "e3", 0.08, cat="crypto")]
    write_cap(tmp_path, 0, items0)
    write_cap(tmp_path, 1, items1)
    c = m.run_map([tmp_path], *span())["change_counts"]
    assert c["ch232/first_crossings/b0.10/outward/nonsports_excrypto/rewarded"]["total"] == 1
    assert c["ch232/first_crossings/b0.10/outward/sports/unrewarded"]["total"] == 1
    assert c["ch232/first_crossings/b0.10/outward/crypto/unrewarded"]["total"] == 1


def test_movers_bins_and_w(tmp_path):
    # M1 traded up at 0.30 -> 0.35 (w = 0.5 + (0.30 - 0.5) = 0.30); M2 quote-only down at 0.70 -> 0.65 (w = 0.5 - 0.2 = 0.30); M3 sub-threshold
    write_cap(tmp_path, 0, [mk("M1", "e1", 0.30, vol=10), mk("M2", "e2", 0.70, vol=10), mk("M3", "e3", 0.5, vol=10)])
    write_cap(tmp_path, 1, [mk("M1", "e1", 0.35, vol=20), mk("M2", "e2", 0.65, vol=10), mk("M3", "e3", 0.505, vol=30)])
    c = m.run_map([tmp_path], *span())["change_counts"]
    assert c["ch234/movers_traded/0.1-0.5/nonsports_excrypto/unrewarded"]["total"] == 1
    assert c["ch234/movers_quote_only/0.5-0.9/nonsports_excrypto/unrewarded"]["total"] == 1
    assert not any(k.startswith("ch234/movers_") and "0.5-0.9" in k and "traded" in k and "quote" not in k for k in c)
    assert m.collateral_weight(0.05, 0.30) == pytest.approx(0.30)
    assert m.collateral_weight(-0.05, 0.70) == pytest.approx(0.30)
    assert m.collateral_weight(0.05, 0.70) == pytest.approx(0.70)
    assert [m.price_bin(p) for p in (0.05, 0.1, 0.5, 0.9)] == ["lt0.1", "0.1-0.5", "0.5-0.9", "ge0.9"]


def test_mover_market_day_w_sd(tmp_path):
    # one market with 3 traded moves of very different w (price 0.2 up -> w 0.2 ; price 0.8 up -> w 0.8): SD >= 0.1
    seq = [(0.20, 1), (0.22, 2), (0.80, 3), (0.82, 4)]
    for k, (p, v) in enumerate(seq):
        write_cap(tmp_path, k, [mk("X", "e1", p, vol=v)])
    res = m.run_map([tmp_path], *span())
    assert res["market_day_aggregates"]["ch234/mover_market_days_ge2_traded/nonsports_excrypto/unrewarded"] == 1
    assert res["shares"]["ch234/share_w_sd_ge_0.1/nonsports_excrypto/unrewarded"] == 1.0


def _event(prefix, bids, vol=0.0, two=None, nr=True):
    out = []
    for i, bid in enumerate(bids):
        two_i = True if two is None else two[i]
        item = mk(f"{prefix}{i}", prefix, bid + 0.005, vol=vol, nr=nr, two=two_i)
        out.append(item)
    return out


def test_complete_event_detection_hb_and_crossing(tmp_path):
    # event E (3 members) complete at both captures; hb0 = 1 - 0.99 = +0.01 (within 2 ticks), hb1 = 1 - 1.02 = -0.02 (zero crossed).
    # event F (2 members) incomplete at capture 1 (a member is one-sided).
    write_cap(tmp_path, 0, _event("E", [0.33, 0.33, 0.33]) + _event("F", [0.5, 0.5]))
    write_cap(tmp_path, 1, _event("E", [0.34, 0.34, 0.34]) + _event("F", [0.5, 0.5], two=[True, False]))
    res = m.run_map([tmp_path], *span())
    lv, ch = res["level_counts"], res["change_counts"]
    s = "nonsports_excrypto/unrewarded"
    assert lv[f"ch233/events/{s}"]["total"] == 4 and lv[f"ch233/member_rows/{s}"]["total"] == 10
    assert lv[f"ch233/event_captures/2/{s}"]["total"] == 2
    assert lv[f"ch233/complete_event_captures/2/{s}"]["total"] == 1
    assert lv[f"ch233/complete_event_captures/3-5/{s}"]["total"] == 2
    assert res["complete_share_by_size_bucket"][f"ch233/complete_share/2/{s}"] == pytest.approx(0.5)
    assert res["complete_share_by_size_bucket"][f"ch233/complete_share/3-5/{s}"] == 1.0
    hbs = sorted(res["hb_quantiles"][s].items())
    assert res["hb_quantiles"][s]["n"] == 3  # E twice and F once
    assert ch[f"ch233/headroom_zero_crossings/{s}"]["total"] == 1
    assert lv[f"ch233/hb_within_2_ticks/{s}"]["total"] >= 2  # E at k0 (+0.01) and E at k1 (-0.02)
    assert hbs


def test_hb_value_and_bucket_helpers(tmp_path):
    write_cap(tmp_path, 0, _event("E", [0.25, 0.25, 0.25]))
    res = m.run_map([tmp_path], *span())
    q = res["hb_quantiles"]["nonsports_excrypto/unrewarded"]
    assert q["n"] == 1 and q["q50"] == pytest.approx(0.25)
    assert [m.size_bucket(n) for n in (1, 2, 3, 5, 6, 10, 11)] == [None, "2", "3-5", "3-5", "6-10", "6-10", "11+"]


def test_within_event_sd(tmp_path):
    # 4-member event, 50 captures; member 0's bid alternates, siblings' bid-sum change differs across members -> SD > 1 tick
    for k in range(50):
        b0 = 0.30 + (0.05 if k % 2 else 0.0)
        write_cap(tmp_path, k, _event("E", [b0, 0.2, 0.2, 0.2]))
    res = m.run_map([tmp_path], *span(3))
    w = res["ch233_within_event_sd"]["nonsports_excrypto/unrewarded"]
    assert w["events_ge_48_units"] == 1 and w["events_sd_ge_1_tick"] == 1


def test_never_reads_capture_k_plus_one(tmp_path):
    a, bdir = tmp_path / "a", tmp_path / "b"
    base = [lambda: [mk("A", "e1", 0.12)], lambda: [mk("A", "e1", 0.08)]]
    for root, last in ((a, [mk("A", "e1", 0.50, vol=9999)] + _event("Z", [0.1, 0.1])), (bdir, [mk("A", "e1", 0.11, vol=1)])):
        for k in range(2):
            write_cap(root, k, base[k]())
        write_cap(root, 2, last)
    # span covers captures 0 and 1 only: the third capture (differs between a and b) must not influence the output
    end = (T0 + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    ra, rb = m.run_map([a], "2026-10-16T00:00:00Z", end), m.run_map([bdir], "2026-10-16T00:00:00Z", end)
    for r in (ra, rb):
        assert r["captures"]["covered"] == 2
    keep = ("level_counts", "change_counts", "distinct_events_over_span", "market_day_aggregates", "shares", "hb_quantiles")
    assert {k: ra[k] for k in keep} == {k: rb[k] for k in keep}
    # and with the later capture inside the span, capture k's counts do not depend on k + 1: capture 1's counts are identical
    end3 = (T0 + timedelta(hours=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    r3a, r3b = m.run_map([a], "2026-10-16T00:00:00Z", end3), m.run_map([bdir], "2026-10-16T00:00:00Z", end3)
    assert r3a["captures"]["covered"] == r3b["captures"]["covered"] == 3
    assert r3a["change_counts"]["ch232/first_crossings/b0.10/outward/nonsports_excrypto/unrewarded"]["total"] == 1


def test_gap_means_no_previous_capture(tmp_path):
    write_cap(tmp_path, 0, [mk("A", "e1", 0.12)])
    write_cap(tmp_path, 1, [mk("A", "e1", 0.08)], hours=6)  # 6 h later: not capture k - 1
    res = m.run_map([tmp_path], *span())
    assert res["change_counts"] == {} and res["notes"]["previous_capture_gap_too_large"] == 1
    assert res["captures"]["gaps_over_2h30"]


def test_inputs_hashed_and_code_hashes(tmp_path):
    write_cap(tmp_path, 0, [mk("A", "e1", 0.12)])
    res = m.run_map([tmp_path], *span())
    assert len(res["inputs"]) == 3 and all(len(i["sha256"]) == 64 and i["bytes"] > 0 for i in res["inputs"])
    assert set(res["code_sha256"]) == {"boundary_map_ch240.py", "run_ch240_map.py"}


def test_runner_refuses_overwrite_and_caps(tmp_path, monkeypatch):
    write_cap(tmp_path / "snap", 0, [mk("A", "e1", 0.12)])
    out = tmp_path / "o" / "m.json"
    args = ["--snapshot-root", str(tmp_path / "snap"), "--start-utc", "2026-10-16T00:00:00Z", "--end-utc", "2026-10-17T00:00:00Z", "--out", str(out)]
    assert runner.main(args) == 0 and out.exists()
    assert runner.main(args) == 1  # refuses to overwrite
    out2 = tmp_path / "o" / "m2.json"
    monkeypatch.setattr(runner, "_above_cap", lambda gb: True)
    assert runner.main([*args[:-1], str(out2), "--data-dumps-cap-gb", "0.0001"]) == 75
    assert not out2.exists()


def test_volume_only_from_sidecar_and_missing_row_unusable(tmp_path):
    # volume24hr in rows is ignored (constant 777); a market with no sidecar row at k is unusable; an absent column in rows is irrelevant
    write_cap(tmp_path, 0, [mk("A", "e1", 0.30, vol=10), mk("B", "e2", 0.30, vol=10)])
    items = [mk("A", "e1", 0.35, vol=20), mk("B", "e2", 0.35, vol=20)]
    d = write_cap(tmp_path, 1, items)
    with gzip.open(d / "rows_ext.csv.gz", "wt", newline="") as fh:  # drop B's sidecar row at k
        w = csv.DictWriter(fh, fieldnames=ECOLS)
        w.writeheader()
        w.writerow(items[0][1])
    res = m.run_map([tmp_path], *span())
    c = res["change_counts"]
    assert c["ch234/movers_traded/0.1-0.5/nonsports_excrypto/unrewarded"]["total"] == 1
    assert sum(v["total"] for k, v in c.items() if k.startswith("ch234/movers_volume_unusable/")) == 1
    assert res["movers_volume_unusable_per_capture"][0]["movers_volume_unusable"] == 1
    # a stray volume_num column in rows.csv.gz is ignored
    assert "volume_num" not in m.ROW_COLS and "volume_num" in m.EXT_COLS
