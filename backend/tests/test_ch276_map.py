# ruff: noqa: E501
"""CH276 surviving-side census: synthetic stores only (no reads of real data)."""

from __future__ import annotations

import builtins
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

from astrolabe.research_lab import ch276_map as m

_P = Path(__file__).resolve().parents[1] / "scripts" / "run_ch276_map.py"
_spec = importlib.util.spec_from_file_location("run_ch276_map_under_test", _P)
runner = importlib.util.module_from_spec(_spec)
sys.modules["run_ch276_map_under_test"] = runner
_spec.loader.exec_module(runner)

T0 = datetime(2026, 10, 16, 0, 31, tzinfo=UTC)
N = 36  # captures 0..35 in the sidecar; the engine also has k = 36 (the k + 1 of the last counted capture)
MODEL = "se0_champion_lr_mm"
RCOLS = ["market_id", "event_id", "received_utc", "closed", "active", "binary", "best_bid", "best_ask", "liquidity", "end_date", "condition_id", "clob_token_id_0", "neg_risk_market_id"]
ECOLS = ["market_id", "received_utc", "clob_token_id_1", "uma_resolution_statuses", "accepting_orders", "fee_type", "fee_category", "series_slugs", "fees_enabled", "fee_schedule", "order_price_min_tick_size", "created_at"]
FEE_0 = '{"exponent":1,"rate":0,"rebateRate":0,"takerOnly":true}'
FAR = "2027-01-01T00:00:00Z"
OLD = "2026-09-01T00:00:00Z"
PROP = '["proposed"]'
DISP = '["proposed","disputed"]'
START = None  # set below


def tcap(k):
    return T0 + timedelta(hours=2 * k)


def iso(d):
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")


def cid(k):
    return f"{tcap(k):%Y%m%dT%H%M%S}Z_{k:08x}"


START_TS = (tcap(12) - timedelta(seconds=600)).timestamp()
END_TS = (tcap(36) - timedelta(seconds=600)).timestamp()
END64 = iso(tcap(26) + timedelta(hours=20))


def M(mid, ev, bid, ask, uma="[]", grp="", created=OLD, end=FAR, cat="politics", liq=50000):
    return dict(mid=mid, ev=ev, bid=bid, ask=ask, uma=uma, grp=grp, created=created, end=end, cat=cat, liq=liq)


def world(k, ev_level=False, mut=False):
    L = []
    if k <= 18:  # group g1: A = 11 is proposed at k = 16 and leaves the listing at k = 19; B = 12, 13, 14 never carry a status of their own
        ab = (0.50, 0.52) if (mut and k > 16) else (0.94, 0.96)
        L.append(M(11, "evG", *ab, PROP if k >= 16 else "[]", "g1"))
    sib = PROP if (ev_level and k >= 16) else "[]"
    L.append(M(12, "evG", 0.01, 0.02, sib, "g1"))
    L.append(M(13, "evG", "", 0.05, sib, "g1"))
    L.append(M(14, "evG", 0.28 if k <= 15 else 0.30, 0.32, sib, "g1"))
    # one-sided proposal rows at k = 18
    L.append(M(31, "ev31", 0.98 if k >= 18 else 0.97, "" if k >= 18 else 0.98, PROP if k >= 18 else "[]"))
    L.append(M(32, "ev32", "" if k >= 18 else 0.02, 0.02 if k >= 18 else 0.03, PROP if k >= 18 else "[]"))
    # insurance classes at k = 20; the markets leave the listing at k = 24
    if k < 24:
        pre = {41: (0.96, 0.97), 42: (0.96, 0.97), 43: (0.96, 0.97), 44: (0.02, 0.03)}
        post = {41: (0.97, 0.98), 42: (0.999, 1.0), 43: (0.985, 0.995), 44: (0.002, 0.004)}
        for mid in (41, 42, 43, 44):
            b, a = (post if k >= 20 else pre)[mid]
            if mut and k > 20:
                b, a = 0.50, 0.52
            L.append(M(mid, f"ev{mid}", b, a, PROP if k >= 20 else "[]"))
    # a dispute: proposed at 14, disputed 15..17, gone at 18; and one disputed at the feed start
    if k <= 17:
        L.append(M(51, "ev51", 0.93, 0.95, "[]" if k < 14 else PROP if k == 14 else DISP))
    if k <= 6:
        L.append(M(52, "ev52", 0.50, 0.52, DISP if k <= 3 else "[]"))
    # crossings
    L.append(M(61, "ev61", 0.94 if k >= 25 else 0.90, 0.96 if k >= 25 else 0.92, PROP if k >= 28 else "[]"))
    if k >= 20:
        L.append(M(62, "ev62", 0.96, 0.97, created=iso(tcap(20) - timedelta(hours=1))))
    L.append(M(63, "ev63", 0.96, 0.97))
    L.append(M(64, "ev64", 0.04 if k >= 26 else 0.08, 0.06 if k >= 26 else 0.10, end=END64))
    L.append(M(65, "ev65", 0.94 if k >= 5 else 0.90, 0.96 if k >= 5 else 0.92))
    L.append(M(71, "ev71", 0.94, 0.96, PROP if k >= 20 else "[]", cat="sports"))
    if k == 31:  # rows the engine's k + 1 lookup reads: the surviving side of three one-sided markets
        L += [M(121, "ev121", 0.62, ""), M(122, "ev122", "", 0.58), M(123, "ev123", 0.60, "")]
    return L


def write_snapshots(root: Path, ks, **kw):
    for k in ks:
        d = root / cid(k)
        d.mkdir(parents=True)
        (d / "manifest.json").write_text(json.dumps({"state": "complete", "started_utc": iso(tcap(k))}))
        items = world(k, **kw)
        with gzip.open(d / "rows.csv.gz", "wt", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=RCOLS)
            w.writeheader()
            for it in items:
                w.writerow({"market_id": it["mid"], "event_id": it["ev"], "received_utc": iso(tcap(k) + timedelta(seconds=60)), "closed": "false", "active": "true", "binary": "1", "best_bid": it["bid"],
                            "best_ask": it["ask"], "liquidity": it["liq"], "end_date": it["end"], "condition_id": f"c{it['mid']}", "clob_token_id_0": f"t0_{it['mid']}", "neg_risk_market_id": it["grp"]})
        with gzip.open(d / "rows_ext.csv.gz", "wt", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=ECOLS)
            w.writeheader()
            for it in items:
                w.writerow({"market_id": it["mid"], "received_utc": iso(tcap(k) + timedelta(seconds=120)), "clob_token_id_1": f"t1_{it['mid']}", "uma_resolution_statuses": it["uma"], "accepting_orders": "true",
                            "fee_type": "", "fee_category": it["cat"], "series_slugs": "", "fees_enabled": "1", "fee_schedule": FEE_0, "order_price_min_tick_size": "0.01", "created_at": it["created"]})


QIDS = [101, 102, 103, 104, 105, 111, 112, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 140]
UP = {101: 60000, 102: 40000, 103: 30000, 104: 20000, 105: 10000, 131: 30000, 132: 31000, 133: 32000}


def write_engine(eng: Path, ks, mut=False):
    for sub in ("quotes", "features", "predictions", "logs"):
        (eng / sub).mkdir(parents=True, exist_ok=True)
    (eng / "logs" / "resolutions-20261017.jsonl").write_text(json.dumps({"market_id": 121, "state": "resolved", "y": 1, "closed_time": "2026-10-17 01:00:00+00"}) + "\n")
    feat_ids = QIDS
    for k in ks:
        spread = 0.01 if k < 12 else 0.03
        mid = 0.6 + (0.1 if (mut and k >= 32) else 0.0)
        rows = []
        for i in QIDS:
            st = 0
            if k == 31 and i in (121, 122, 123):
                st = 3
            if k == 31 and i == 125:
                st = 1
            if k == 31 and i == 126:
                st = 2
            if k == 31 and i == 124:
                continue  # absent from the listing
            rows.append((i, st))
        ids = [r[0] for r in rows]
        sts = np.array([r[1] for r in rows], np.int8)
        bid = np.where(sts == 0, mid - spread / 2, np.nan)
        ask = np.where(sts == 0, mid + spread / 2, np.nan)
        pq.write_table(pa.table({"market_id": pa.array(ids, pa.int64()), "t_off": pa.array([1.0] * len(ids), pa.float32()), "bid": pa.array(bid, pa.float32()), "ask": pa.array(ask, pa.float32()), "st": pa.array(sts, pa.int8())}),
                       eng / "quotes" / f"{cid(k)}.parquet")
        if k == 36:
            continue
        ev = ["E1" if i in (101, 102, 103, 104, 105) else "E2" if i in (111, 112) else "E3" if i in (131, 132, 133) else f"s{i}" for i in feat_ids]
        neg = [1.0 if i in (101, 102, 103, 104, 105, 111, 112, 131, 132, 133) else 0.0 for i in feat_ids]
        cat = ["sports" if i == 140 else "politics" for i in feat_ids]
        n = len(feat_ids)
        pq.write_table(pa.table({"market_id": pa.array(feat_ids, pa.int64()), "event_id": ev, "category": cat, "ms_neg_risk": pa.array(neg, pa.float32()), "ms_log_liq": pa.array([math.log1p(50000)] * n, pa.float32()),
                                 "ms_hours_to_end": pa.array([100.0] * n, pa.float32()), "end_ts": pa.array([np.nan] * n, pa.float64())}), eng / "features" / f"{cid(k)}.parquet")
        pd_ = eng / "predictions" / cid(k)
        pd_.mkdir(parents=True, exist_ok=True)
        up = np.array([UP.get(i, 20000) for i in feat_ids], np.uint16)
        pq.write_table(pa.table({"elig": pa.array([15] * n, pa.uint8()), "dir_2h_dn": pa.array([1000] * n, pa.uint16()), "dir_2h_up": pa.array(up, pa.uint16())}), pd_ / f"{MODEL}.parquet")


def write_monitor(mon: Path, mut=False):
    mon.mkdir(parents=True, exist_ok=True)
    t_k_a = (tcap(16) + timedelta(seconds=120)).timestamp()
    t_exit_a = tcap(19).timestamp()
    t_k_41 = (tcap(20) + timedelta(seconds=120)).timestamp()
    pr = (lambda p: p + 0.07) if mut else (lambda p: p)
    sz = 1.0 if not mut else 3.0

    def tr(ts, cond, side, oi, cash, price=0.5):
        return {"key": f"k{ts}{cond}", "recv_ts": ts + 30, "ts": ts, "condition_id": cond, "token_id": "x", "side": side, "outcome_index": oi, "size": sz * cash / max(price, 0.01), "price": pr(price), "cash": cash, "wallet_hash": "SECRET",
                "tx16": "0", "title": "t", "slug": "s"}

    ev = [tr(t_k_a + 600, "c11", "SELL", 0, 5000.0), tr(t_k_a + 900, "c11", "BUY", 0, 3000.0), tr(t_exit_a + 100, "c11", "SELL", 0, 4000.0), tr(t_k_a + 1000, "c11", "SELL", 0, 500.0),
          tr(t_k_a - 3600, "c11", "BUY", 1, 2000.0), tr(t_k_a - 100000, "c11", "SELL", 1, 2000.0),
          tr(t_k_41 + 300, "c41", "SELL", 0, 1500.0), tr(t_k_41 + 400, "c44", "BUY", 0, 2000.0)]
    by_day: dict = {}
    for r in ev:
        by_day.setdefault(datetime.fromtimestamp(r["ts"], UTC).strftime("%Y%m%d"), []).append(r)
    for d, rs in by_day.items():
        (mon / f"trades-{d}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rs))
    gap_lo, gap_hi = tcap(20).timestamp() + 3600, tcap(20).timestamp() + 5400
    cyc, t = [], tcap(0).timestamp()
    while t <= tcap(36).timestamp():
        if not (gap_lo < t < gap_hi):
            cyc.append({"cycle_start_utc": datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "new_trades": 3, "status": "ok"})
        t += 300
    (mon / "stats.jsonl").write_text("".join(json.dumps(c) + "\n" for c in cyc))
    for decoy in ("alerts.jsonl", "wallets.jsonl", "outcomes.jsonl", "scores-20261017.jsonl"):
        (mon / decoy).write_text("DECOY_NEVER_READ\n")


def write_rules(rules: Path):
    rules.mkdir(parents=True)
    (rules / "20261017.jsonl").write_text(json.dumps({"key": "m:61", "kind": "row", "reason": "new", "slot": "x", "data": {"question": "Will the scheduled vote pass?", "description": "Resolves on the official results."}}) + "\n")


def build(base: Path, **kw):
    base = base / "research_lab"
    snaps, eng, rules, mon = base / "snapshots", base / "signal_engine", base / "stream_gamma_rules", base / "live_trades"
    snaps.mkdir(parents=True)
    write_snapshots(snaps, range(N), **{k: v for k, v in kw.items() if k in ("ev_level", "mut")})
    write_engine(eng, range(N + 1), mut=kw.get("mut", False))
    write_rules(rules)
    write_monitor(mon, mut=kw.get("mut", False))
    return base


def run(base: Path):
    periods = (("2026-10-16", "2026-10-16"), ("2026-10-17", "2026-10-17"))
    return m.run_map([base / "snapshots"], base / "signal_engine", base / "stream_gamma_rules", base / "live_trades", START_TS, END_TS, 1, 12, periods, MODEL)


@pytest.fixture(scope="module")
def store(tmp_path_factory):
    return build(tmp_path_factory.mktemp("s"))


@pytest.fixture(scope="module")
def result(store):
    return run(store)


# --------------------------------------------------------------------------------------------------------------- lines


def test_field_semantics_is_the_first_line_and_per_market(result):
    keys = list(result)
    assert keys[:3] == ["version", "kind", "line_1_field_semantics"]
    l1 = result["line_1_field_semantics"]
    assert l1["semantics_reading"] == "per_market" and l1["sibling_carry_share"] == 0.0
    assert l1["siblings_of_first_seen_proposals"]["proposed_markets_first_seen_in_groups_ge2"] == 1  # market 11 at k = 16
    assert l1["siblings_of_first_seen_proposals"]["siblings_total"] == 3 and l1["siblings_of_first_seen_proposals"]["unflagged_empty_status"] == 3
    # the proposal of A (list length 1) in a group of 4 at k = 16, 17, 18; the member count with a status is 1
    assert l1["status_list_length_vs_neg_risk_group_size"]["len_lt_group_size"] == 3
    assert l1["status_list_length_vs_members_with_any_status"]["len_eq_members_with_status"] == 3
    assert l1["group_captures"]["group_captures_with_any_status"] == 3


def test_field_semantics_event_level_reading_and_no_b_units(tmp_path):
    res = run(build(tmp_path, ev_level=True))
    l1 = res["line_1_field_semantics"]
    assert l1["semantics_reading"] == "event_level" and l1["sibling_carry_share"] == 1.0
    assert l1["group_captures"]["groups_all_statused_members_identical_string"] >= 1
    assert res["line_6_b_units"]["b_units_total"] == 0 and res["line_6_b_units"]["b_candidate_classes_excluded_or_counted"]["own_status_at_k"] == 3
    assert res["decisions"]["ch273"]["drafted"] is False


def test_line_2_one_sided_proposal_rows_by_surviving_side(result):
    l2 = result["line_2_one_sided_proposal_rows"]
    assert l2["not_two_sided_rows"] == 2 and l2["not_two_sided_rows_by_surviving_side"] == {"ask_only": 1, "bid_only": 1}
    assert l2["by_surviving_side_x_favoured_side"] == {"ask_only|no": 1, "bid_only|yes": 1}
    assert l2["by_surviving_side_x_tier"] == {"ask_only|10k-100k": 1, "bid_only|10k-100k": 1}
    assert l2["consistency_with_m1_j0_funnel_not_two_sided"]["equal"] is True
    assert l2["first_seen_proposal_rows_in_scope"] == 9  # 11, 31, 32, 41-44, 51, 61; the sports market 71 is out of scope


def test_line_3_negrisk_events_with_three_or_more_eligible_members(result):
    l3 = result["line_3_negrisk_events_ge3"]
    assert l3["captures_with_features"] == 12 and l3["eligible_rows"] == 12 * 20 - 6  # six markets are not two-sided at k = 31
    assert l3["negrisk_events_with_co_n_ge_3"] == 24 and l3["eligible_rows_in_negrisk_events_with_co_n_ge_3"] == 12 * 8
    assert l3["share_eligible_rows_in_negrisk_events_with_co_n_ge_3"] == pytest.approx(96 / 234)
    sd1 = float(np.std(np.array([59000, 39000, 29000, 19000, 9000]) / 65535.0, ddof=1))
    sd3 = float(np.std(np.array([29000, 30000, 31000]) / 65535.0, ddof=1))
    assert l3["within_event_sd_of_s_2h"]["n_event_captures"] == 24
    assert l3["within_event_sd_of_s_2h"]["median"] == pytest.approx(m.median([sd1, sd3] * 12))
    assert l3["between_event_sd_of_event_mean_s_2h"]["n_captures"] == 12
    assert result["decisions"]["ch270"]["built"] is True


def test_line_4_k_plus_1_states_and_ox(result):
    l4 = result["line_4_k_plus_1_state"]
    s = l4["by_state"]
    assert l4["eligible_rows_with_k_plus_1_capture"] == 234
    assert s["one_sided_sign_determinable_up"] == 1 and s["one_sided_sign_determinable_down"] == 1 and s["one_sided_indeterminate"] == 1
    assert s["absent"] == 1 and s["closed"] == 1 and s["inactive"] == 1 and s["labelled"] == 234 - 6
    assert l4["share_sign_determinable_one_sided"] == pytest.approx(2 / 234)
    assert result["decisions"]["ch271_b"]["built"] is False  # 0.85% against the 1% line: reported, not tuned
    assert l4["by_state_x_mid_bin_k"]["one_sided_sign_determinable_up"]["0.5-0.9"] == 1
    assert l4["by_state_x_hours_to_end_k"]["absent"]["3-14d"] == 1
    ox = l4["ox_1s_84"]
    assert ox["eligible_rows"] == 234 and ox["rows_with_ox_1s_84_gt_0"] == 12  # ids 121-123 at k = 32..35
    assert ox["rows_full_84_slot_history"] == 0 and ox["distribution_rows_by_count"]["1-2"] == 12
    assert result["decisions"]["ch271_c"]["built"] is True


def test_line_5_monitor_prints_in_the_window_only(result):
    l5 = result["line_5_monitor_prints"]
    assert l5["available"] is True
    assert l5["units_with_any_print_in_window_a_day"] == {"2026-10-17": 3}  # 11, 41, 44
    assert l5["units_with_fill_flow_print_in_window_a_day"] == {"2026-10-17": 3}
    assert l5["units_with_any_print_in_window"] == 3 and l5["prints_in_unit_windows"] == 4  # the $500 print and the print after t_exit are not counted
    assert l5["units_total"] == 7 and l5["units_censored_no_exit_in_span"] == 1  # market 61 never leaves the listing
    assert l5["pre_k_24h"]["units_with_any_print"] == 1 and l5["pre_k_24h"]["units_with_fill_flow_print"] == 1  # the print 24 h + before t_k is not
    assert l5["monitor_cycles"]["gaps"] == 1
    assert l5["share_of_covered_unit_windows_overlapping_a_cycle_gap"] == pytest.approx(4 / 7)  # 41-44
    assert l5["side_outcome_forms_seen_all_prints_ge_1000"]["BUY|outcome_index=1"] == 1
    assert l5["median_units_with_any_print_per_full_day"] == 1.5  # [3, 0] over the two full days
    assert result["decisions"]["ch272"]["filed_as_m1_amendment"] is False


def test_line_6_b_units(result):
    l6 = result["line_6_b_units"]
    assert l6["b_units_total"] == 3 and l6["b_units_two_sided"] == 2 and l6["b_units_no_bid_ask_only"] == 1
    assert l6["no_bid_share_of_b_units"] == pytest.approx(1 / 3)
    assert l6["two_sided_b_units_a_day"] == {"2026-10-17": 2}
    assert l6["by_group_size_x_book_state"] == {"3-5|ask_only": 1, "3-5|two_sided": 2}
    assert l6["two_sided_bid_moved_vs_unmoved_k_minus_1_to_k"] == {"moved": 1, "unmoved": 1}  # 14 moved, 12 did not
    assert l6["E_B"]["b_units_in_engine_eligible_form"] == 1  # 14 (mid 0.31); 12 sits under 0.02
    assert l6["median_two_sided_b_units_per_full_day"] == 1.0  # [2, 0]
    assert result["decisions"]["ch273"]["drafted"] is False  # 1 against the 25 a day line


def test_line_7_crossings(result):
    l7 = result["line_7_near_certain_first_crossings"]
    assert l7["crossings_total"] == 1 and l7["by_rules_class"] == {"scheduled": 1} and l7["crossings_a_day"] == {"2026-10-18": 1}
    assert l7["by_tier"] == {"10k-100k": 1} and l7["by_hours_to_end_bin"] == {"ge60d": 1}
    assert l7["born_certain"] == 1  # market 62 listed at 0.96
    assert l7["pre_window_certain_by_window_start"] >= 3  # 63, 65 (crossed in the warm-up) and the markets already certain at the feed start
    assert l7["crossing_candidates_excluded"] == {"end_within_24h": 1}  # market 64, a NO-side crossing
    assert l7["proposed_before_end_date"] == {"units_with_a_proposal_in_span": 1, "proposed_before_end_date": 1, "share": 1.0, "note": l7["proposed_before_end_date"]["note"]}
    assert l7["classed_share"] == 1.0
    assert result["decisions"]["ch274"]["built"] is False


def test_line_8_insurance_classes_and_disputes(result):
    l8 = result["line_8_insurance_and_disputes"]
    assert l8["proposal_units_total"] == 7
    assert l8["by_insurance_class"] == {"uninsured": 1, "middle": 1, "insured": 5}  # 42 | 44 | 11, 41, 43, 51, 61
    assert l8["insured_units_scaled_to_21_days"] == pytest.approx(5 * 21 / 2)
    assert l8["disputed_state_first_appearances_in_scope"] == 1 and l8["disputed_already_present_at_feed_start_excluded"] == 1
    assert l8["duration_in_captures_in_scope"] == {"ended_runs": 1, "median_captures": 3.0, "max_captures": 3, "right_censored_runs": 0}
    assert l8["proposal_events_in_scope_first_seen_rows"] == 9
    assert l8["disputes_share_of_proposal_events_first_seen_rows"] == pytest.approx(1 / 9)
    assert l8["of_which_preceded_by_a_proposal_state_in_the_feed"] == 1
    assert result["decisions"]["ch275"]["goes_to_census"] is False  # 52.5 insured units scaled to 21 days against the 100 line
    assert "1 - bid" in l8["insurance_class_definition"]["ins_k"]


def test_line_9_spread_ops_line(result):
    per = result["line_9_spread_ops_line"]["periods"]
    a, b = per["2026-10-16..2026-10-16"], per["2026-10-17..2026-10-17"]
    assert a["captures_read"] == 12 and b["captures_read"] == 12
    assert a["all"]["p50_spread_all_tiers"] == pytest.approx(0.01) and b["all"]["p50_spread_all_tiers"] == pytest.approx(0.03)
    assert b["all"]["p50_10k-100k"] == pytest.approx(0.03)
    assert b["nonsports_excrypto"]["rows"] < b["all"]["rows"]  # the sports row (140) is only in "all"


def test_output_schema_hash_and_rss(result):
    for k in ("version", "kind", "span", "decisions", "not_mapped", "inputs", "code_sha256", "peak_rss_mb", "decision_lines", "rules_stream", "notes"):
        assert k in result, k
    assert set(result["code_sha256"]) >= {"ch276_map.py", "run_ch276_map.py", "m1_j0.py"}
    assert all(len(v) == 64 for v in result["code_sha256"].values())
    assert result["peak_rss_mb"] > 0 and "counts only" in result["kind"]
    assert all(i["sha256"] for i in result["inputs"])
    json.dumps(result, default=str)
    assert result["span"]["counted_captures"] == 24 and result["span"]["full_days"] == ["2026-10-17", "2026-10-18"]


def test_decisions_are_none_when_counts_are_unavailable(tmp_path):
    base = build(tmp_path)
    res = m.run_map([base / "snapshots"], base / "signal_engine", base / "stream_gamma_rules", None, START_TS, END_TS, 1, 12, (("2026-10-16", "2026-10-16"), ("2026-10-17", "2026-10-17")), MODEL)
    assert res["line_5_monitor_prints"]["available"] is False
    assert res["decisions"]["ch272"]["filed_as_m1_amendment"] is None


# --------------------------------------------------------------------------------------------------------------- the no-post-k rule and the forbidden reads


def test_no_post_k_value_changes_the_counts(tmp_path, result):
    res2 = run(build(tmp_path, mut=True))  # prices of A and the insurance units after their k, the engine mids from k = 32, and every print's price and size change
    assert res2["line_8_insurance_and_disputes"]["by_insurance_class"] == result["line_8_insurance_and_disputes"]["by_insurance_class"]
    assert res2["line_8_insurance_and_disputes"]["zone_counts_of_1_minus_bid_k"] == result["line_8_insurance_and_disputes"]["zone_counts_of_1_minus_bid_k"]
    assert res2["line_6_b_units"] == result["line_6_b_units"]
    assert res2["line_2_one_sided_proposal_rows"] == result["line_2_one_sided_proposal_rows"]
    assert res2["line_4_k_plus_1_state"]["by_state"] == result["line_4_k_plus_1_state"]["by_state"]
    assert res2["line_5_monitor_prints"] == result["line_5_monitor_prints"]
    assert res2["line_7_near_certain_first_crossings"] == result["line_7_near_certain_first_crossings"]


def test_reads_only_allowed_columns_and_paths(tmp_path, monkeypatch):
    base = build(tmp_path)
    opened: list[str] = []
    cols: list = []
    real_open, real_gz, real_rt, real_rs = builtins.open, gzip.open, pq.read_table, pq.read_schema

    def spy_open(f, *a, **k):
        opened.append(str(f))
        return real_open(f, *a, **k)

    def spy_gz(f, *a, **k):
        opened.append(str(f))
        return real_gz(f, *a, **k)

    def spy_rt(f, *a, **k):
        opened.append(str(f))
        cols.append(tuple(k.get("columns") or ()))
        return real_rt(f, *a, **k)

    def spy_rs(f, *a, **k):
        opened.append(str(f))
        return real_rs(f, *a, **k)

    monkeypatch.setattr(builtins, "open", spy_open)
    monkeypatch.setattr(gzip, "open", spy_gz)
    monkeypatch.setattr(pq, "read_table", spy_rt)
    monkeypatch.setattr(pq, "read_schema", spy_rs)
    run(base)
    monkeypatch.undo()
    bad = [p for p in opened if any(x in p for x in ("/logs/", "resolutions-", "alerts.jsonl", "wallets.jsonl", "outcomes.jsonl", "scores-", "holdout", "/labels"))]
    assert not bad, bad
    assert any(p.endswith("stats.jsonl") for p in opened) and any("trades-" in p for p in opened)
    flat = {c for t in cols for c in t}
    assert flat and not [c for c in flat if c in m.FORBIDDEN_EXACT or any(s in c for s in m.FORBIDDEN_SUBSTR)]
    assert flat <= {"market_id", "bid", "ask", "st", "event_id", "category", "ms_neg_risk", "ms_log_liq", "ms_hours_to_end", "end_ts", "dir_2h_dn", "dir_2h_up"}


def test_guards_refuse_forbidden_fields_paths_and_output_keys():
    for col in ("y", "closed_time", "wallet_hash", "proxyWallet", "payoff_usd", "winner", "res_7d", "label_dir"):
        with pytest.raises(m.Refusal):
            m.guard_columns(["market_id", col])
    m.guard_columns(["uma_resolution_statuses", "outcome_index", "best_bid"])  # named by section E
    for p in ("/x/signal_engine/logs/resolutions-20261017.jsonl", "/x/live_trades/alerts.jsonl", "/x/live_trades/wallets.jsonl", "/x/live_trades/outcomes.jsonl", "/x/live_trades/scores-20261017.jsonl"):
        with pytest.raises(m.Refusal):
            m.guard_path(Path(p))
    m.guard_path(Path("/x/live_trades/trades-20261017.jsonl"))
    for key in ("p_value", "edge", "profit_usd", "pnl_total", "sharpe"):
        with pytest.raises(m.Refusal):
            m.check_output({"a": {key: 1}})
    m.check_output({"line_1": {"insurance_class_edges": 1}})


# --------------------------------------------------------------------------------------------------------------- runner


def test_runner_refusals_cap_exit_codes_and_write_once(store, tmp_path, monkeypatch):
    base = ["--snapshot-root", str(store / "snapshots"), "--engine-root", str(store / "signal_engine"), "--rules-root", str(store / "stream_gamma_rules"), "--monitor-root", str(store / "live_trades")]
    span = ["--start-utc", iso(datetime.fromtimestamp(START_TS, UTC)), "--end-utc", iso(datetime.fromtimestamp(END_TS, UTC)), "--engine-days", "1"]
    out = store / "ch276_map" / "CH276_map.json"
    assert runner.main([*base, "--out", str(tmp_path / "x.json"), *span]) == 2  # outside research_lab
    assert runner.main(["--snapshot-root", str(tmp_path / "snapshots"), "--engine-root", str(store / "signal_engine"), "--rules-root", str(store / "stream_gamma_rules"), "--out", str(out), "--last-days", "1"]) == 2
    other = tmp_path / "research_lab" / "elsewhere"
    other.mkdir(parents=True)
    assert runner.main(["--snapshot-root", str(store / "snapshots"), "--engine-root", str(store / "signal_engine"), "--rules-root", str(store / "stream_gamma_rules"), "--monitor-root", str(other), "--out", str(out), "--last-days", "1"]) == 2  # not live_trades
    assert runner.main([*base, "--out", str(out)]) == 2  # neither a span nor --last-days
    monkeypatch.setattr(runner, "_above_cap", lambda gb: True)
    assert runner.main([*base, "--out", str(out), *span, "--data-dumps-cap-gb", "0"]) == 75
    monkeypatch.undo()
    assert runner.main([*base, "--out", str(out), *span]) == 0
    written = json.loads(out.read_text())
    assert list(written)[2] == "line_1_field_semantics" and written["version"] == m.VERSION and written["peak_rss_mb"] > 0 and written["code_sha256"]["ch276_map.py"]
    assert runner.main([*base, "--out", str(out), *span]) == 1  # refuses to overwrite
    monkeypatch.setattr(m, "run_map", lambda *a, **k: (_ for _ in ()).throw(m.Refusal("forbidden")))
    assert runner.main([*base, "--out", str(store / "ch276_map" / "o3.json"), *span]) == 3


def test_helpers():
    assert m.list_len('["a","b"]') == 2 and m.list_len("[]") == 0 and m.list_len("['a', 'b', 'c']") == 3 and m.list_len("proposed, disputed") == 2
    assert m.book_state(0.5, 0.6) == "two_sided" and m.book_state(0.5, math.nan) == "bid_only" and m.book_state(math.nan, 0.4) == "ask_only"
    assert m.book_state(0.6, 0.5) == "crossed_or_locked" and m.book_state(math.nan, math.nan) == "no_quote"
    assert [m.ins_class(x) for x in (0.002, 0.0021, 0.01, 0.0101, 0.06)] == ["uninsured", "middle", "middle", "insured", "insured"]
    assert m.fill_flow("SELL", "YES", 0) and m.fill_flow("BUY", "YES", 1) and not m.fill_flow("BUY", "YES", 0) and m.fill_flow("BUY", "NO", 0) and m.fill_flow("SELL", "NO", 1)
    assert m.hte_bin(24 * 2) == "lt3d" and m.hte_bin(24 * 5) == "3-14d" and m.hte_bin(24 * 100) == "ge60d" and m.hte_bin(math.nan) == "missing"
