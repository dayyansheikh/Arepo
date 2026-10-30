# ruff: noqa: E501
"""CH269 census and tails map: synthetic stores only (no reads of real data)."""

from __future__ import annotations

import csv
import gzip
import importlib.util
import json
import math
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from astrolabe.research_lab import census_map_ch269 as m

_P = Path(__file__).resolve().parents[1] / "scripts" / "run_ch269_map.py"
_spec = importlib.util.spec_from_file_location("run_ch269_map_under_test", _P)
runner = importlib.util.module_from_spec(_spec)
sys.modules["run_ch269_map_under_test"] = runner
_spec.loader.exec_module(runner)

T0 = datetime(2026, 10, 16, 0, 31, tzinfo=UTC)
N = 30
MODEL = "se0_champion_lr_mm"
RCOLS = ["market_id", "event_id", "received_utc", "closed", "active", "binary", "best_bid", "best_ask", "liquidity", "end_date"]
ECOLS = ["market_id", "fee_type", "fee_category", "series_slugs", "fees_enabled", "fee_schedule", "accepting_orders", "open_interest", "volume_num", "uma_resolution_statuses", "trap_column"]
FEE_0 = '{"exponent":1,"rate":0,"rebateRate":0,"takerOnly":true}'
FAR = "2027-01-01T00:00:00Z"


def tcap(k):
    return T0 + timedelta(hours=2 * k)


def cid(k):
    return f"{tcap(k):%Y%m%dT%H%M%S}Z_{k:08x}"


def row(mid, ev, bid, ask, end=FAR, cat="politics", uma="[]", k=0):
    return ({"market_id": mid, "event_id": ev, "received_utc": tcap(k).strftime("%Y-%m-%dT%H:%M:%SZ"), "closed": "false", "active": "true", "binary": "1", "best_bid": bid, "best_ask": ask, "liquidity": "50000", "end_date": end},
            {"market_id": mid, "fee_type": "", "fee_category": cat, "series_slugs": "", "fees_enabled": "1", "fee_schedule": FEE_0, "accepting_orders": "true", "open_interest": "", "volume_num": "10", "uma_resolution_statuses": uma, "trap_column": "NEVER"})


def sidecar_items(k):
    it = [row(1, "e1", 0.94, 0.96, uma='["proposed"]' if k >= 17 else "[]", k=k),
          row(2, "e2", 0.49, 0.51, end="2026-10-17T05:00:00Z", k=k),
          row(3, "e3", 0.94, 0.96, cat="sports", uma='["proposed"]' if k >= 17 else "[]", k=k),
          row(4, "e4", 0.49, 0.51, k=k), row(5, "e5", 0.49, 0.51, k=k)]
    if k >= 18:
        it.append(row(7, "e7", 0.94, 0.96, uma='["proposed"]', k=k))  # first seen already proposed: no k - 1 row
    return it


def write_snapshots(root: Path, ks):
    for k in ks:
        d = root / cid(k)
        d.mkdir(parents=True)
        (d / "manifest.json").write_text(json.dumps({"state": "complete", "started_utc": tcap(k).strftime("%Y-%m-%dT%H:%M:%SZ")}))
        for name, cols, idx in (("rows.csv.gz", RCOLS, 0), ("rows_ext.csv.gz", ECOLS, 1)):
            with gzip.open(d / name, "wt", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
                w.writeheader()
                for it in sidecar_items(k):
                    w.writerow(it[idx])


def mid_of(mid, k):
    if mid == 4:
        return 0.020 if k < 20 else 0.012 if k == 20 else 0.008
    if mid == 5:
        return 0.020 if k < 23 else 0.009
    return 0.5


def write_engine(eng: Path, ks, missing_quotes=(7,)):
    (eng / "quotes").mkdir(parents=True)
    (eng / "features").mkdir()
    (eng / "logs").mkdir()
    for k in ks:
        if k in missing_quotes:
            continue
        ids = [i for i in (1, 2, 3, 4, 5) if not (i == 5 and k == 14)]
        mids = np.array([mid_of(i, k) for i in ids])
        pq.write_table(pa.table({"market_id": pa.array(ids, pa.int64()), "t_off": pa.array([1.0] * len(ids), pa.float32()), "bid": pa.array(mids - 0.0005, pa.float32()), "ask": pa.array(mids + 0.0005, pa.float32()), "st": pa.array([0] * len(ids), pa.int8())}),
                       eng / "quotes" / f"{cid(k)}.parquet")
        fids = [1, 2, 3, 4, 5]
        pq.write_table(pa.table({"market_id": pa.array(fids, pa.int64()), "category": ["politics", "politics", "sports", "politics", "politics"], "ms_log_liq": pa.array([math.log1p(50000)] * 5, pa.float32()),
                                 "mo_chg_1d": pa.array([0.01 * i for i in fids], pa.float32())}), eng / "features" / f"{cid(k)}.parquet")
        pd_ = eng / "predictions" / cid(k)
        pd_.mkdir(parents=True)
        up = np.array([60000, 30000, 65000, 20000, 10000], np.uint16)
        pq.write_table(pa.table({"elig": pa.array([15] * 5, pa.uint8()), "dir_2h_dn": pa.array([1000] * 5, pa.uint16()), "dir_2h_up": pa.array(up, pa.uint16())}), pd_ / f"{MODEL}.parquet")
    (eng / "logs" / "resolutions-20261018.jsonl").write_text(
        json.dumps({"market_id": 4, "state": "resolved", "y": 0, "closed_time": "2026-10-18 01:00:00+00", "fetched_utc": "2026-10-18T02:00:00Z"}) + "\n"
        + json.dumps({"market_id": 99, "state": "not_found", "y": None, "fetched_utc": "2026-10-18T02:00:00Z"}) + "\n")


def write_rules(rules: Path):
    rules.mkdir(parents=True)
    (rules / "20261017.jsonl").write_text(
        json.dumps({"key": "m:2", "kind": "row", "reason": "new", "slot": "x", "data": {"question": "Will the scheduled vote pass?", "description": "Resolves on the official results."}}) + "\n"
        + json.dumps({"key": "m:3", "kind": "hash", "sha": "ab"}) + "\n")


@pytest.fixture(scope="module")
def store(tmp_path_factory):
    base = tmp_path_factory.mktemp("s") / "research_lab"
    snaps, eng, rules = base / "snapshots", base / "signal_engine", base / "stream_gamma_rules"
    snaps.mkdir(parents=True)
    write_snapshots(snaps, range(N))
    write_engine(eng, range(N))
    write_rules(rules)
    return base


@pytest.fixture(scope="module")
def result(store):
    return m.run_map([store / "snapshots"], store / "signal_engine", store / "stream_gamma_rules", "2026-10-16T00:00:00Z", "2026-10-18T14:00:00Z", 45, 35, MODEL)


def test_proposals_counted_once_and_unavailable_disclosed(result):
    p = result["proposals_ch263"]
    assert p["units_all_categories"] == 2  # market 1 (ELIG) and market 3 (sports) at slot 17; market 7 has no k - 1 row
    assert p["units_by_category"]["nonsports_excrypto"] == 1 and p["units_by_category"]["sports"] == 1
    assert p["unavailable_first_seen"]["no_k_minus_1_row"] >= 1
    assert p["nonsports_excrypto_by_tier"]["10k-100k"] == 1
    assert p["nonsports_excrypto_by_ladder_position"] == {"standalone": 1}
    assert p["nonsports_excrypto_side_readability"] == {"readable": 1}
    assert p["per_day_nonsports_excrypto"]["2026-10-17"] == 1
    assert "2026-10-17" in p["full_days_used_for_the_line"]
    assert p["median_per_full_day_nonsports_excrypto"] == 1.0


def test_overdue_unit_one_shot_and_open_interest_presence(result):
    o = result["overdue_ch264"]
    assert o["units_fresh"] == 1 and o["per_day"]["2026-10-17"] == 1
    assert o["tercile_variable"] == "liquidity_proxy" and o["open_interest_presence"]["non_empty"] == 0
    assert o["units_by_rule_class"] == {"scheduled": 1}
    assert o["classed_share"] == 1.0 and o["end_date_moved_share"] == 0.0
    assert o["stock_interior_overdue_per_capture"]["max"] == 1
    assert result["decisions"]["m2_ch264"]["drafted"] is False


def test_closes_usable_and_class(result):
    c = result["closes_ch267"]
    assert c["closes_seen_total"] == 1 and c["days_with_full_coverage"] == ["2026-10-17"]
    assert c["closes_per_full_day"]["2026-10-17"] == 1 and c["usable_share"] == 1.0
    assert c["class_split_usable_closes"] == {"scheduled": 1}
    assert c["median_scheduled_usable_per_full_day"] == 1.0
    assert result["decisions"]["lt15_ch267"]["drafted"] is False
    assert result["rules_stream"]["classes_n"] == {"scheduled": 1}


def test_missing_engine_capture_listed_not_reconstructed(result):
    q = result["captures_engine"]["quotes"]
    assert q["missing"] == 1 and q["missing_slots_utc"] == [tcap(7).strftime("%Y-%m-%dT%H:%MZ")]
    assert q["present"] == N - 1


def test_crossings_display_and_placebo_first_units(result):
    c = result["tails_ch266_sketch_crossings"]
    assert c["display_units_nonsports_excrypto_per_day"]["2026-10-17"] == 2  # markets 4 and 5 (market 5 crosses both lines in one slot)
    assert c["placebo_units_nonsports_excrypto_per_day"]["2026-10-17"] == 1  # market 4 at 0.012
    assert c["display_units_two_sided_at_k_plus_1_share"] == 1.0
    assert c["zone_half_spread_nonsports_excrypto_rows"] >= 2
    assert result["decisions"]["ch266_sketch"]["kept"] is False


def test_label_store_bins_use_last_quote(result):
    arms = result["tails_ch266_map_label_store"]["arms"]
    g = arms["last_two_sided_quote_any"]["groups"]["nonsports_excrypto"]
    assert g["n_with_quote"] == 1
    assert sum(b["n"] for b in g["bins_0.1c"].values()) == 1 and sum(b["wins"] for b in g["bins_0.1c"].values()) == 0
    assert result["tails_ch266_map_label_store"]["label_store_resolved_with_y"] == 1
    assert result["tails_ch266_map_label_store"]["label_store_states"]["not_found"] == 1


def test_champion_top_decile_and_fragile_and_residual(result):
    t = result["champion_top_decile_ch262"]
    assert t["captures"] == N - 1  # all engine captures with quotes, predictions and features
    assert t["top_decile_units_per_capture"]["median"] == 1  # 4 eligible non-sports rows -> ceil(0.4) = 1
    assert t["top_decile_units_per_capture_by_tier"]["10k-100k"]["median"] == 1
    assert result["decisions"]["lt14_ch262"]["drafted"] is False
    assert t["fee_class_split_totals"].get("fee_free", 0) > 0  # sidecar-covered captures carry the capture's own fee class
    f = result["fragile_ch268"]
    assert f["rows_used_all_eligible"] > 0 and f["share_positive_all_eligible"] > 0  # market 5 absent at slot 14
    assert result["residual_ch265"]["labelled_rows"] > 0


def test_output_schema_and_hash(result):
    for k in ("version", "kind", "span", "sidecar_captures", "rules_stream", "proposals_ch263", "overdue_ch264", "closes_ch267", "tails_ch266_sketch_crossings", "tails_ch266_map_label_store",
              "champion_top_decile_ch262", "residual_ch265", "fragile_ch268", "decisions", "not_mapped", "inputs", "code_sha256", "peak_rss_mb", "captures_engine"):
        assert k in result, k
    assert set(result["code_sha256"]) >= {"census_map_ch269.py"}
    assert "kind" in result and "counts only" in result["kind"]
    assert all(i["sha256"] for i in result["inputs"])
    assert "ask_size_1_coverage" in result["not_mapped"]
    json.dumps(result, default=str)


def test_runner_refusals_and_write_once(store, tmp_path):
    base = ["--snapshot-root", str(store / "snapshots"), "--engine-root", str(store / "signal_engine"), "--rules-root", str(store / "stream_gamma_rules")]
    out = store / "ch269_map" / "CH269_map.json"
    assert runner.main([*base, "--out", str(tmp_path / "x.json"), "--start-utc", "a", "--end-utc", "b"]) == 2  # outside research_lab
    assert runner.main(["--snapshot-root", str(tmp_path / "snapshots"), "--engine-root", str(store / "signal_engine"), "--rules-root", str(store / "stream_gamma_rules"), "--out", str(out), "--last-days", "1"]) == 2
    nox = store.parent / "research_lab_empty" / "research_lab"
    (nox / "snapshots").mkdir(parents=True)
    assert runner.main(["--snapshot-root", str(nox / "snapshots"), "--engine-root", str(nox / "signal_engine"), "--rules-root", str(nox / "stream_gamma_rules"), "--out", str(nox / "o.json"), "--last-days", "1"]) == 2  # roots missing
    assert runner.main([*base, "--out", str(out), "--start-utc", "2026-10-16T00:00:00Z", "--end-utc", "2026-10-18T14:00:00Z"]) == 0
    assert json.loads(out.read_text())["version"] == m.VERSION
    assert runner.main([*base, "--out", str(out), "--last-days", "1"]) == 1  # refuses to overwrite
    assert runner.main([*base, "--out", str(store / "ch269_map" / "o2.json"), "--last-days", "1", "--data-dumps-cap-gb", "0"]) in (0, 75)


def test_helpers():
    assert m.tier_of(999) == 0 and m.tier_of(5e4) == 2 and m.tier_of(float("nan")) == 4
    lo, hi = m.wilson(5, 100)
    assert 0.02 < lo < 0.05 < hi < 0.12
    assert m.classify_rule("hit $100k at any time") == "barrier" and m.classify_rule("the fomc decision, scheduled") == "scheduled" and m.classify_rule("hello") == "other"
