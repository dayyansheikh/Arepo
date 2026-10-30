# ruff: noqa: E501
"""M1-J0 (CH263) counts-only pre-freeze check: synthetic stores under tmp_path only (no reads of real data)."""

from __future__ import annotations

import csv
import gzip
import importlib.util
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from astrolabe.research_lab import m1_j0 as j0

_P = Path(__file__).resolve().parents[1] / "scripts" / "run_m1_j0.py"
_spec = importlib.util.spec_from_file_location("run_m1_j0_under_test", _P)
runner = importlib.util.module_from_spec(_spec)
sys.modules["run_m1_j0_under_test"] = runner
_spec.loader.exec_module(runner)

T0 = datetime(2026, 10, 20, 0, 31, tzinfo=UTC)
N = 40
MISSING_K = 15
RCOLS = ["market_id", "event_id", "received_utc", "closed", "active", "binary", "best_bid", "best_ask", "liquidity", "end_date", "clob_token_id_0", "spread"]
ECOLS = ["market_id", "received_utc", "clob_token_id_1", "uma_resolution_statuses", "accepting_orders", "fee_type", "fee_category", "series_slugs",
         "fees_enabled", "fee_schedule", "order_price_min_tick_size", "outcome_trap"]
FEE_0 = '{"exponent":1,"rate":0,"rebateRate":0,"takerOnly":true}'
P, E, PD = '["proposed"]', "[]", '["proposed","disputed"]'


def tcap(k):
    return T0 + timedelta(hours=2 * k)


def iso(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def cid(k):
    return f"{tcap(k):%Y%m%dT%H%M%S}Z_{k:08x}"


def spec(k):
    """(market, event, bid, ask, status, category, closed) present at capture k."""
    out = [(1, "e1", "0.9413", "0.9613", P if k >= 5 else E, "politics", "false"),
           (2, "e2", "0.02", "0.04", P if k >= 6 else E, "Finance:US", "false"),
           (3, "e3", "0.94", "0.96", P if k >= 5 else E, "sports", "false"),
           (4, "e4", "0.50", "0.52", P if k >= 7 else E, "politics", "false"),
           (5, "e5", "0.94", "0.96", PD if k == 8 else E, "politics", "false"),
           (6, "e6", "0", "0.99", P if k >= 9 else E, "politics", "false"),
           (8, "e8", "0.94", "0.96", P if k in (1, 10, 11) else E, "politics", "false"),
           (9, "e9", "0.94", "0.96", P if k >= 11 else E, "politics", "false"),
           (10, "e9", "0.01", "0.03", P if k >= 11 else E, "politics", "false"),
           (11, "e11", "0.94", "0.96", P if k >= 16 else E, "politics", "false"),
           (12, "e12", "0.94", "0.96", P if k >= 12 else E, "politics", "true")]
    if k >= 10:
        out.append((7, "e7", "0.94", "0.96", P, "politics", "false"))  # first seen already proposed: no k - 1 row
    return out


def write_stores(root: Path, sweeps: dict | None = None) -> tuple[Path, Path, Path]:
    snap = root / "research_lab" / "snapshots"
    sw = root / "research_lab" / "book_sweeps"
    eng = root / "research_lab" / "signal_engine"
    for k in range(N):
        if k == MISSING_K:
            continue
        d = snap / cid(k)
        d.mkdir(parents=True)
        (d / "manifest.json").write_text(json.dumps({"state": "complete", "started_utc": iso(tcap(k)), "capture_id": cid(k)}))
        rec = iso(tcap(k) + timedelta(minutes=3))
        with gzip.open(d / "rows.csv.gz", "wt", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(RCOLS)
            for mid, ev, bid, ask, _u, _c, closed in spec(k):
                w.writerow([mid, ev, rec, closed, "true", "1", bid, ask, "50000", "2026-10-20T00:00:00Z", f"t{mid}_0", ""])
        with gzip.open(d / "rows_ext.csv.gz", "wt", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(ECOLS)
            for mid, _ev, _b, _a, uma, cat, _cl in spec(k):
                w.writerow([mid, rec, f"t{mid}_1", uma, "true", "", cat, "", "false", FEE_0, "0.001", "YES_WON_SECRET"])
    sw.mkdir(parents=True)
    for k, rows in (sweeps or {}).items():
        d = sw / f"sweep_{k:03d}"
        d.mkdir()
        (d / "manifest.json").write_text(json.dumps({"state": "complete", "series_index": 0, "snapshot_id": cid(k)}))
        with gzip.open(d / "rows.csv.gz", "wt", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["token_id", "market_id", "batch_receipt_utc", "best_bid", "best_ask", "ask_size_1", "state"])
            for tok, asz in rows:
                w.writerow([tok, tok[1:].split("_")[0], iso(tcap(k) + timedelta(minutes=9)), "0.94", "0.9613", asz, "two_sided"])
    (eng / "state").mkdir(parents=True)
    (eng / "state" / "labels.json").write_text(json.dumps({"res_candidates": {"1": 1.0e9}}))
    return snap, sw, eng


SWEEPS = {5: [("t1_0", "100")], 6: [("t2_1", "")]}


@pytest.fixture()
def rep(tmp_path):
    snap, sw, eng = write_stores(tmp_path, SWEEPS)
    return j0.run_j0(snap, sw, eng, tcap(0).timestamp(), tcap(N).timestamp(), warmup=2)


def test_status_code_forms():
    assert j0.status_code("[]") == (0, False)
    assert j0.status_code('["proposed"]') == (1, False)
    assert j0.status_code('["Proposed","Disputed"]') == (2, True)
    assert j0.status_code('["disputed"]') == (2, False)
    assert j0.status_code('["resolved"]') == (3, False)
    assert j0.status_code("something") == (4, False)


def test_units_and_classes(rep):
    f = rep["funnel"]
    assert rep["eligible_units"]["total"] == 4  # markets 1 (YES), 2 (NO), 9 and 10 (ladder)
    assert rep["splits_counts"]["S5_side"] == {"NO": 2, "YES": 2}
    assert rep["splits_counts"]["S3_ladder"] == {"member_loser": 1, "member_winner": 1, "standalone": 2}
    assert rep["splits_counts"]["S8_members"] == {"1": 2, "2-5": 2}
    assert f["disputed_at_k"] == 1 and f["contested"] == 1 and f["not_two_sided"] == 1
    assert f["out_of_scope_sports"] == 1 and f["not_open_at_k"] == 1
    assert f["prior_proposal_state"] == 1 and rep["prior_proposal_state_gap"] == {"<=24h": 1}
    assert f["no_k_minus_1_row"] == 1
    assert f["no_previous_capture"] >= 1 and f["already_proposed"] > 0
    assert rep["unavailable_by_category"]["no_k_minus_1_row|nonsports_excrypto"] == 1
    assert rep["eligible_units"]["events"] == 3
    assert rep["eligible_units"]["units_per_event_projected"] == {"1": 2, "2-3": 1}


def test_s2_uses_category_key(rep):
    s2 = rep["splits_counts"]["S2_fee_category"]
    assert tuple(s2) == j0.S2_CELLS
    assert s2["politics"] == 3 and s2["finance"] == 1 and sum(s2.values()) == 4
    assert "Finance:US -> finance" in rep["s2_raw_fee_category_to_key"]


def test_sweep_coverage_and_receipts(rep):
    sc = rep["sweep_1_coverage"]
    assert sc["covered_finite_ask_size_1"] == 1 and sc["units_with_any_sweep_row"] == 2 and sc["share"] == 0.25
    g = rep["receipt_gaps_s"]
    assert g["sidecar_minus_row"]["median"] == 0.0
    assert g["sweep_minus_row"]["n"] == 2 and g["sweep_minus_row"]["median"] == 360.0
    assert rep["engine_resolution_candidates"]["units_in_candidates"] == 1


def test_status_forms_and_transitions(rep):
    sf = rep["status_forms"]
    assert sf["rows_with_both_propos_and_disput"] == 1
    t = sf["transitions_between_consecutive_captures"]
    assert t["empty->disputed"] == 1 and t["disputed->empty"] == 1 and t["proposed->empty"] >= 1


def test_span_decisions_and_missing_slot(rep):
    sp = rep["span"]
    assert sp["missing_slots_utc"] == [tcap(MISSING_K).strftime("%Y-%m-%dT%H:%MZ")]
    assert len(sp["warmup_captures"]) == 2 and sp["full_days"] == ["2026-10-22"]
    d = rep["decisions"]
    assert d["median_full_day_units"] == 0.0 and d["rule_a_extend_to_42_days"] is True and d["rule_b_extend_to_42_days"] is True


def test_no_price_size_or_outcome_printed(rep):
    s = json.dumps(rep)
    for sentinel in ("0.9613", "0.9413", "0.0387", "YES_WON_SECRET", "outcome_trap", "100.0"):
        assert sentinel not in s
    assert rep["splits_counts"]["S6_zone"] == {"(0.005,0.01]": 1, "(0.01,0.03]": 1, "(0.03,0.10]": 2}


def test_strict_time_order_enforced(tmp_path):
    snap, sw, _ = write_stores(tmp_path)
    caps, _ = j0.discover_captures(snap, tcap(0).timestamp(), tcap(N).timestamp())
    assert [c["start"] for c in caps] == sorted(c["start"] for c in caps)
    jp = j0.J0Pass(0)
    jp.feed(caps[1], None)
    with pytest.raises(ValueError):
        jp.feed(caps[0], None)


def test_first_complete_capture_per_slot(tmp_path):
    snap, _, _ = write_stores(tmp_path)
    d = snap / "later_duplicate"
    d.mkdir()
    (d / "manifest.json").write_text(json.dumps({"state": "complete", "started_utc": iso(tcap(3) + timedelta(minutes=10))}))
    (d / "rows.csv.gz").write_bytes((snap / cid(3) / "rows.csv.gz").read_bytes())
    caps, _ = j0.discover_captures(snap, tcap(0).timestamp(), tcap(N).timestamp())
    assert [c["id"] for c in caps if c["slot"] == caps[3]["slot"]] == [cid(3)]


def test_runner_refusals_and_write_once(tmp_path):
    snap, sw, eng = write_stores(tmp_path, SWEEPS)
    out = tmp_path / "research_lab" / "m1_j0" / "M1_J0.json"
    base = ["--snapshot-root", str(snap), "--sweep-root", str(sw), "--engine-root", str(eng), "--start-utc", iso(tcap(0)), "--end-utc", iso(tcap(N)), "--warmup-captures", "2"]
    assert runner.main(base[:2] + ["--sweep-root", str(snap)] + base[4:] + ["--out", str(out)]) == 2
    assert runner.main(base + ["--out", str(tmp_path / "elsewhere.json")]) == 2
    assert runner.main(base + ["--out", str(out)]) == 0
    first = out.read_text()
    assert json.loads(first)["eligible_units"]["total"] >= 1
    assert runner.main(base + ["--out", str(out)]) == 1
    assert out.read_text() == first
    assert runner.main(["--snapshot-root", str(snap), "--sweep-root", str(sw), "--last-days", "8", "--out", str(out.with_name("b.json"))]) == 0


def test_float_edges_rounded_to_6dp():
    assert j0.zone_of(1 - 0.97) == "(0.01,0.03]"  # 0.030000000000000027 unrounded
    assert j0.zone_of(1 - 0.995) == "(0.001,0.005]"
    assert j0.zone_of(1 - 0.999) == "c<=0.001"
    assert j0.tick_of("0.0010000000001") == "0.001" and j0.tick_of("0.01") == "0.01" and j0.tick_of("") == "other_or_missing"


def test_mid_edge_and_empty_event_id(tmp_path, monkeypatch):
    def edge_spec(k):
        st = P if k >= 5 else E
        return [(21, "", "0.85", "0.95", st, "politics", "false"),   # (0.85 + 0.95) / 2 = 0.8999999999999999 unrounded: YES after rounding
                (22, "", "0.03", "0.05", st, "politics", "false"),   # NO: ask_f = 0.97, c = 0.03 -> (0.01,0.03] after rounding
                (23, "e23", "0.84", "0.95", st, "politics", "false")]  # mid 0.895: contested
    monkeypatch.setattr(sys.modules[__name__], "spec", edge_spec)
    snap, sw, eng = write_stores(tmp_path)
    rep = j0.run_j0(snap, sw, eng, tcap(0).timestamp(), tcap(N).timestamp(), warmup=2)
    assert rep["version"] == "m1-j0-v2"
    assert rep["eligible_units"]["total"] == 2 and rep["funnel"]["contested"] == 1
    assert rep["eligible_units"]["events"] == 2  # two empty event_ids are two one-market events
    assert rep["splits_counts"]["S3_ladder"] == {"standalone": 2} and rep["splits_counts"]["S8_members"] == {"1": 2}
    assert rep["splits_counts"]["S6_zone"] == {"(0.01,0.03]": 1, "(0.03,0.10]": 1}
