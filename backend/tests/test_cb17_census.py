# ruff: noqa: E501
"""CB17 counts-only pre-censuses q0400-q0403 (offline; synthetic worn-window files). Counts only: no mark, outcome, wallet or later capture reaches a result."""

from __future__ import annotations

import json
from collections import Counter

import pytest

from astrolabe.research_lab import cb13_label as lab
from astrolabe.research_lab import cb17_census as cen
from astrolabe.research_lab import cb17_common as c17
from astrolabe.research_lab import cb17_pre as pre
from tests.cb17_synth import (
    ep,
    fill_row,
    print_,
    stamp,
    write_capture,
    write_day,
    write_screen,
    write_sweep,
)

H = 3600.0
D12 = ep("2026-10-12T00:00:00Z")
SECRETS = ("WALLET-SECRET", "k-secret", "SECRET-MARK", "RESOLVED_SECRET")


def assert_no_forbidden(doc) -> None:
    c17.assert_clean_result(doc)
    txt = json.dumps(doc)
    for s in SECRETS:
        assert s not in txt


# ---- field-restricted readers -------------------------------------------------------------------------------------------------------------------


def test_iter_cols_refuses_a_field_outside_the_whitelist_and_never_copies_the_rest(tmp_path):
    d = write_capture(tmp_path / "snapshots", "2026-10-12T00:00:00Z", [{"mid": "1", "cid": "c1", "eid": "E1", "bid": "0.48", "ask": "0.50"}])
    rows = list(cen.iter_cols(d / "rows.csv.gz", ("market_id", "best_bid", "volume24hr"), c17.CAPTURE_FIELDS))
    assert rows == [("1", "0.48", "5")]
    for bad in (("chg_1h",), ("last_trade_price",), ("market_id", "updated_at")):
        with pytest.raises(c17.Refused, match="not whitelisted"):
            list(cen.iter_cols(d / "rows.csv.gz", bad, c17.CAPTURE_FIELDS))
    with pytest.raises(c17.Refused, match="not whitelisted"):
        list(cen.iter_cols(d / "rows_ext.csv.gz", ("market_id", "uma_resolution_statuses"), c17.SIDECAR_FIELDS))
    with pytest.raises(c17.Refused, match="not whitelisted"):
        list(cen.iter_cols(d / "rows_ext.csv.gz", ("open_interest",), c17.SIDECAR_FIELDS))


def test_iter_dir_cols_skips_and_counts_rows_at_or_after_the_cutoff(tmp_path):
    d = write_capture(tmp_path / "snapshots", "2026-10-15T23:59:00Z", [{"mid": "1", "cid": "c1", "eid": "E1", "bid": "0.48", "ask": "0.50", "recv": ep("2026-10-15T23:59:30Z")},
                                                                       {"mid": "2", "cid": "c2", "eid": "E2", "bid": "0.48", "ask": "0.50", "recv": ep("2026-10-16T00:00:00Z")},
                                                                       {"mid": "3", "cid": "c3", "eid": "E3", "bid": "0.48", "ask": "0.50", "recv": ep("2026-10-16T00:05:00Z")}])
    stats: Counter = Counter()
    rows = list(cen.iter_dir_cols(d, "rows.csv.gz", ("market_id",), c17.CAPTURE_FIELDS, "received_utc", stats))
    assert [r[0] for r in rows] == ["1"] and stats["rows_at_or_after_cutoff_skipped"] == 2


def test_list_stamped_never_opens_a_directory_at_or_after_the_cutoff_or_before_the_start(tmp_path):
    snap = tmp_path / "snapshots"
    for nm in ("20261011T200000Z_aa11", "20261016T000000Z_bb22", "20261026T000000Z_cc33"):  # garbage: opening any of them would raise
        (snap / nm).mkdir(parents=True)
        (snap / nm / "rows.csv.gz").write_bytes(b"not gzip")
    write_capture(snap, "2026-10-12T00:00:00Z", [{"mid": "1", "cid": "c1", "eid": "E1", "bid": "0.48", "ask": "0.50"}])
    stats: Counter = Counter()
    got = cen.list_stamped(snap, c17.CAPTURE_DIR_RE, c17.CENSUS_START, stats)
    assert [d.name[:8] for d, _ in got] == ["20261012"] and stats["dirs_at_or_after_cutoff_not_opened"] == 2
    assert [d.name[:8] for d, _ in cen.list_stamped(snap, c17.CAPTURE_DIR_RE, c17.CAPTURE_LOOKBACK_START, Counter())] == ["20261012"]


def test_iter_monitor_adds_side_and_recv_ts_only_on_request_and_never_wallet_or_key(tmp_path):
    tr = tmp_path / "live_trades"
    write_day(tr, "20261012", [print_(D12 + 100, "c1", 0.5, tx="t1")])
    write_day(tr, "20261015", [print_(ep("2026-10-15T23:59:00Z"), "c1", 0.5, tx="t2"), print_(ep("2026-10-16T00:00:00Z"), "c1", 0.5, tx="t3")])
    stats: Counter = Counter()
    plain = list(cen.iter_monitor(tr, stats))
    assert [p["tx16"] for p in plain] == ["t1", "t2"] and stats["prints_at_or_after_cutoff_skipped"] == 1 and stats["monitor_days_missing"] == 2
    for p in plain:
        assert "side" not in p and "recv_ts" not in p and not ({"key", "wallet_hash", "wallet", "ctx_chg_1h", "ctx_status"} & set(p))
    assert all(p["side"] == "BUY" and "recv_ts" not in p for p in cen.iter_monitor(tr, Counter(), side=True))
    assert all(p["recv_ts"] == p["ts"] + 400 and "side" not in p for p in cen.iter_monitor(tr, Counter(), lag=True))
    (tmp_path / "live_trades" / "trades-20261016.jsonl").write_text("x")  # a day outside the window is never listed (CENSUS_DAYS) and the guard refuses it by name
    with pytest.raises(c17.Refused):
        c17.guard_monitor_file(tmp_path / "live_trades" / "trades-20261016.jsonl")


def test_read_fills_refuses_holdout_paths_and_fills_at_or_after_the_cutoff(tmp_path):
    ok = write_screen(tmp_path, [fill_row(1, "c1", D12 + 7200, -1)])
    stats: Counter = Counter()
    fills = cen.read_fills(ok, stats)
    assert len(fills) == 1 and "mark_2h" not in fills[0] and "p_vwap" not in fills[0] and fills[0]["d"] == -1.0
    late = write_screen(tmp_path / "late", [fill_row(1, "c1", ep("2026-10-16T00:00:01Z"), -1)])
    with pytest.raises(c17.Refused, match="cut-off"):
        cen.read_fills(late, Counter())
    ho = tmp_path / "creative_batch13" / "t_holdout"
    ho.mkdir(parents=True)
    with pytest.raises(c17.Refused):
        cen.read_fills(ho, Counter())
    assert cen.read_fills(write_screen(tmp_path / "ns", [fill_row(1, "c1", D12 + 7200, -1, status="no_touch")]), stats) == [] and stats["fills_not_fill_status"] == 1


# ---- q0400: pre-census A / E --------------------------------------------------------------------------------------------------------------------


def a_world(tmp_path, *, side_flip=0, late_wide_capture=True, straddling_wide_capture=False, blank_side_first=False, zero_size_first=False):
    """Market 1 (6 x [open YES-buy, close YES-sell, open NO-buy]) and market 2 (4 open YES-buy) plus one sports fill; captures 00:00, 00:31:03 (pinned), 02:00, 04:00 (and a wide later one)."""
    root = tmp_path / "w"
    snap, tr = root / "snapshots", root / "live_trades"
    q1 = {"mid": "1", "cid": "c1", "eid": "E1", "bid": "0.48", "ask": "0.50", "created": "2026-10-11T12:00:00Z"}
    q2 = {"mid": "2", "cid": "c2", "eid": "E2", "bid": "0.48", "ask": "0.50", "created": "2026-10-12T01:00:00Z"}
    q3 = {"mid": "3", "cid": "c3", "eid": "E3", "bid": "0.48", "ask": "0.50", "fee_type": "sports_fees", "fee_category": "sports", "series": '["nfl-2026"]'}
    for st, nm in (("2026-10-12T00:00:00Z", None), ("2026-10-12T00:31:03Z", "20261012T003103Z_2df48d64"), ("2026-10-12T02:00:00Z", None), ("2026-10-12T04:00:00Z", None), ("2026-10-15T22:31:02Z", "20261015T222102Z_2eae9aa6")):
        write_capture(snap, st, [q1, q2, q3], name=nm)
    if straddling_wide_capture:  # starts before every transaction but its LAST page is after them: its time is that last page, so it can never be a touch
        write_capture(snap, "2026-10-12T02:09:00Z", [{**q1, "bid": "0.10", "ask": "0.90"}, {**q2, "bid": "0.10", "ask": "0.90"}], last_page_offset=3600.0)
    if late_wide_capture:  # received AFTER every transaction: must never be the touch of any of them
        write_capture(snap, "2026-10-12T05:00:00Z", [{**q1, "bid": "0.10", "ask": "0.90"}, {**q2, "bid": "0.10", "ask": "0.90"}])
    fills, prints = [], []
    t = D12 + 2 * H + 600
    i = 0
    for _k in range(6):
        for kind in ("open_yes", "close_yes", "open_no"):
            ts = t + 40.0 * i
            oi, side, d = (0, "BUY", -1) if kind == "open_yes" else (0, "SELL", 1) if kind == "close_yes" else (1, "BUY", 1)
            if side_flip and i < side_flip:
                side = "SELL" if side == "BUY" else "BUY"
            prints.append(print_(ts, "c1", 0.50, oi=oi, side=side, tx=f"txA{i}"))
            fills.append(fill_row(i, "c1", ts, d))
            i += 1
    for _k in range(4):
        ts = t + 40.0 * i
        prints.append(print_(ts, "c2", 0.50, oi=0, side="BUY", tx=f"txB{i}", mkt="2", ev="E2"))
        fills.append(fill_row(i, "c2", ts, -1, mkt="2", ev="E2"))
        i += 1
    ts = t + 40.0 * i
    prints.append(print_(ts, "c3", 0.50, oi=0, side="BUY", tx="txS", fee="sports_fees", title="Chiefs vs Bills", mkt="3", ev="E3"))
    fills.append(fill_row(i, "c3", ts, -1, mkt="3", ev="E3", label=lab.SPORTS))
    if blank_side_first:
        prints[0]["side"] = ""
    if zero_size_first:
        prints[0]["size"] = 0
    write_day(tr, "20261012", prints)
    write_day(tr, "20261015", [print_(ep("2026-10-16T00:00:30Z"), "c1", 0.5, tx="txLATE")])  # after the cut-off: skipped and counted
    screen = write_screen(root, fills)
    return {"screen": screen, "tr": tr, "snap": snap}


def run_a(w):
    return cen.pre_census_A(w["screen"], w["tr"], w["snap"])


def test_pre_census_a_counts_labels_cells_and_side_agreement(tmp_path):
    res = run_a(a_world(tmp_path))
    assert_no_forbidden(res)
    assert res["fills"]["n"] == 23 and res["fills"]["non_sports"] == 22 and res["fills"]["non_sports_resolved"] == 22
    assert res["labels"]["non_sports"] == {"close": 6, "open": 16}
    assert res["both_label_cells"] == {"cells": 3, "with_both": 1, "fills": 12, "markets": 1, "events": 1}
    assert res["side_agreement"]["overall"] == {"n": 22, "k": 22}
    assert res["input_stats"]["prints_at_or_after_cutoff_skipped"] == 1
    # defaults: n = 22 < 800, so the branch is T and A is withdrawn uncounted (never promoted by a small sample)
    assert res["branch"] == "T" and res["a_withdrawn_uncounted"] is True and any("overall n 22 < 800" in r for r in res["side_agreement"]["rule"]["reasons"])
    # the side-signed population: 22 non-sports transactions, each with a touch from a capture BEFORE tau (never the later wide capture)
    assert res["side_signed_population"]["eligible_units"] == 22 and "touch_wide" not in res["side_signed_population"]["excluded_by_reason"]
    assert res["first_day"]["S_units_by_age"] == {"6-24h": 18, "lt6h": 4} and res["first_day"]["markets_with_created_at"] >= 2
    assert set(res["strata"]) == {"selected_population", "selected_level", "touch_consistent_T", "side_signed_S"} and res["strata"]["selected_population"] == "T"


def test_pre_census_a_branch_s_and_the_failing_cell_rule(tmp_path, monkeypatch):
    monkeypatch.setattr(pre, "AGREE_N_MIN", 20)
    monkeypatch.setattr(pre, "CELL_N_MIN", 4)
    monkeypatch.setattr(pre, "WILSON_LOWER_MIN", 0.80)  # n = 22 cannot reach 0.95
    res = run_a(a_world(tmp_path / "s"))
    assert res["branch"] == "S" and res["a_withdrawn_uncounted"] is False and res["strata"]["selected_population"] == "S"
    # two flipped sides in the first (market 1) fills: overall 20/22 = 90.9% < 97% -> branch T, with the failing cells listed
    bad = run_a(a_world(tmp_path / "t", side_flip=2))
    assert bad["branch"] == "T" and bad["side_agreement"]["overall"] == {"n": 22, "k": 20} and bad["a_withdrawn_uncounted"] is True
    assert any("below 97%" in r for r in bad["side_agreement"]["rule"]["reasons"])


def test_pre_census_a_is_deterministic_and_the_result_is_clean(tmp_path):
    w = a_world(tmp_path)
    a, b = run_a(w), run_a(w)
    assert c17.sha256_obj(a) == c17.sha256_obj(b)
    assert not (set(json.dumps(a)) and "txA" in json.dumps(a)) and "WALLET" not in json.dumps(a)
    se = a["planning_se"]
    assert set(se) == {"A1_T_pre_fill_proxy", "A1_S_pre_fill_proxy", "E_T_first_day_proxy", "E_S_first_day_proxy", "recipe", "proxy"}
    for k in ("A1_T_pre_fill_proxy", "A1_S_pre_fill_proxy"):
        assert set(se[k]) <= {"n", "se", "mde", "se_by_way", "g_by_way", "recipe", "note", "mde_over_power_gate"}


def test_pre_census_a_without_a_monitor_day_or_capture_does_not_invent_counts(tmp_path):
    root = tmp_path / "w"
    (root / "snapshots").mkdir(parents=True)
    screen = write_screen(root, [fill_row(1, "c1", D12 + 7200, -1)])
    res = cen.pre_census_A(screen, root / "live_trades", root / "snapshots")
    assert res["fills"]["token_resolution"] == {"no_print": 1} and res["branch"] == "T" and res["side_signed_population"]["eligible_units"] == 0 and res["input_stats"]["monitor_days_missing"] == 4


# ---- q0401: pre-census B -----------------------------------------------------------------------------------------------------------------------


def b_world(tmp_path, passes=8, anomaly=False):
    root = tmp_path / "w"
    snap, sw = root / "snapshots", root / "book_sweeps"
    write_capture(snap, D12 - 60, [{"mid": str(m), "cid": f"c{m}", "eid": f"E{m}", "bid": "0.48", "ask": "0.50"} for m in (1, 2, 3)]
                  + [{"mid": "4", "cid": "c4", "eid": "E4", "bid": "0.48", "ask": "0.50", "fee_type": "sports_fees", "fee_category": "sports", "series": '["nfl-2026"]'}], name=stamp(D12 + 1.0, "aa01aa01"))
    for p in range(passes):
        t = D12 + 7200.0 * p
        old = p % 2 == 1
        for j, off in enumerate((0.0, 120.0)):
            recv = t + off + 5.0
            ts_a = int((recv - (1200.0 if old else 30.0) - (0.0 if j == 0 else off)) * 1000)  # token A: same stamp in both sweeps
            books = [
                {"tok": "A", "mid": "1", "bid": "0.48", "ask": "0.50", "ts": ts_a, "hash": "hA"},
                {"tok": "B", "mid": "2", "bid": "0.48", "ask": "0.50", "ts": int((recv + (100.0 if anomaly else -30.0)) * 1000), "hash": f"hB{j}"},
                {"tok": "C", "mid": "3", "bid": "0.48", "ask": "0.50", "ts": int((recv - 30.0) * 1000), "hash": f"hC{j}", "d5b": 2000 + 300 * j, "d5a": 2000 - 300 * j},
                {"tok": "D", "mid": "4", "bid": "0.48", "ask": "0.50", "ts": int((recv - 30.0) * 1000), "hash": "hD"},
            ]
            write_sweep(sw, t + off, books, name=stamp(t + off, f"{p:02x}{j:02x}0000"))
    return {"sw": sw, "snap": snap}


def test_pre_census_b_counts_stamp_semantics_breathing_book_and_cut_points(tmp_path):
    w = b_world(tmp_path)
    res = cen.pre_census_B(w["sw"], w["snap"])
    assert_no_forbidden(res)
    assert res["sweeps"]["passes"] == 8 and res["sweeps"]["lone_sweeps"] == 0 and res["counts"]["sports_tokens_first_sweeps"] == 8
    assert res["age_bins"] == {"age_600-3600s": 4, "age_lt60s": 20} and res["tokens_with_both_fresh_and_old"] == 1 and res["tokens_seen"] == 3
    assert res["stamp_semantics"] == {"hash_same": 7, "hash_same_stamp_same": 7, "hash_changed": 14, "hash_changed_stamp_changed": 14}
    bb = res["breathing_book"]
    assert bb["pairs_two_sided"] == 21 and bb["touch_unchanged"] == 21 and bb["touch_unchanged_shifted_1to5c"] == 7 and bb["shifted_share_of_touch_unchanged"] == pytest.approx(7 / 21, abs=1e-5)
    # the next-pass table is presence only: 21 tokens are present at the next pass, the last pass's 3 have none
    present = sum(v.get("present", 0) for v in res["next_pass_no_mark_by_age_bin"].values())
    no_pass = sum(v.get("no_pass_in_window", 0) for v in res["next_pass_no_mark_by_age_bin"].values())
    assert present == 21 and no_pass == 3
    cp = res["cut_points"]
    # the imbalance (B5 - A5) / D1 is read at the SECOND sweep: token C's is 0.15 there and 0 at the first sweep
    assert cp["imbalance_terciles"][0] == 0.0 and 0.0 < cp["imbalance_terciles"][1] <= 0.15 and cp["b2_units"] == 21 and cp["units"] == 21
    assert cp["activity_terciles_c"] == [0.0, 0.0] and cp["sd_x"] > 0
    assert set(res["strata"]) == {"B1", "B2"} and res["strata"]["B1"]["selected_level"] in (0, 1, 2) and res["strata"]["B2"]["selected_level"] in (0, 1, 2)
    assert set(res["planning_se"]) == {"B1_L_pre", "B2_dm_pre", "recipe", "proxies"}


def test_pre_census_b_is_deterministic(tmp_path):
    w = b_world(tmp_path, passes=5)
    assert c17.sha256_obj(cen.pre_census_B(w["sw"], w["snap"])) == c17.sha256_obj(cen.pre_census_B(w["sw"], w["snap"]))


def test_pre_census_b_ignores_sweeps_at_or_after_the_cutoff(tmp_path):
    w = b_world(tmp_path, passes=3)
    for nm in ("20261016T000000Z_dead0000", "20261026T000000Z_dead0001"):
        (w["sw"] / nm).mkdir()
        (w["sw"] / nm / "rows.csv.gz").write_bytes(b"not gzip")
    res = cen.pre_census_B(w["sw"], w["snap"])
    assert res["input_stats"]["dirs_at_or_after_cutoff_not_opened"] == 2 and res["sweeps"]["in_window"] == 6


# ---- q0402: pre-census C -----------------------------------------------------------------------------------------------------------------------


def c_captures(snap, *, n=10, r_of=None, closed_at=(), near_end_at=(), dv_zero_at=(), gap_s=7200.0, start=D12):
    """Event E1 = markets m1 (mid moves +1c per capture) and m2 (flat); event E2 = single market m3 (flat). OI / volume per capture chosen so that r_j = 0.1 j (dV = 100)."""
    vol, oi = 0.0, 0.0
    for j in range(n):
        if j > 0:
            dv = 0.0 if j in dv_zero_at else 100.0
            vol += dv
            oi += (r_of(j) if r_of else 0.1 * j) * (dv if dv else 100.0)
        m1_bid = 0.50 + 0.01 * j
        end2 = "2026-10-12T05:00:00Z" if j in near_end_at else "2027-01-01T00:00:00Z"
        rows = [{"mid": "m1", "cid": "c1", "eid": "E1", "bid": f"{m1_bid:.2f}", "ask": f"{m1_bid + 0.02:.2f}", "oi": f"{oi}", "vol": f"{vol}", "closed": "True" if j in closed_at else "False"},
                {"mid": "m2", "cid": "c2", "eid": "E1", "bid": "0.30", "ask": "0.32", "oi": f"{oi}", "vol": f"{vol}", "end": end2},
                {"mid": "m3", "cid": "c3", "eid": "E2", "bid": "0.60", "ask": "0.62", "oi": "5", "vol": f"{vol}"}]
        write_capture(snap, start + gap_s * j, rows)


def test_pre_census_c_trailing_cut_points_never_include_the_current_interval(tmp_path, monkeypatch):
    snap = tmp_path / "w" / "snapshots"
    c_captures(snap)
    calls: list[list[float]] = []
    real = pre.trailing_cuts
    monkeypatch.setattr(pre, "trailing_cuts", lambda vals: (calls.append(list(vals)) or real(vals)))
    res = cen.pre_census_C(snap)
    assert_no_forbidden(res)
    # E1 is eligible at intervals 1..9 (m1 moves +1c each): the j-th call sees exactly r_1..r_(j-1), never r_j or later
    assert len(calls) == 18  # two per eligible interval: the r cut points, then the trailing dV cut points
    for j, prior in enumerate(calls[0::2], start=1):
        assert prior == pytest.approx([0.1 * i for i in range(1, j)])
    for j, prior in enumerate(calls[1::2], start=1):
        assert prior == pytest.approx([100.0] * (j - 1))
    c = res["counts"]
    assert c["eligible_units"] == 9 and c["thin_history"] == 6 and c["units_with_6_prior"] == 3 and c["class_mint"] == 3
    assert c["no_qualifying_member"] == 9 and res["events_with_units_having_6_prior"] == 1  # event E2 never moves
    assert res["oi_changed_share_of_traded"] == pytest.approx(9 / 18, abs=1e-5) and res["splits"]["traded_multi_other"] == 9 and res["splits"]["traded_single"] == 9
    assert "no k+1 row is read" in res["rule"]
    assert res["strata"]["levels"]["level2"]["denominator"] == 3


def test_pre_census_c_classes_come_from_prior_intervals_only(tmp_path):
    """r_7 is far above every earlier r (mint-heavy), r_8 far below (merge-heavy): the classes follow the PRIOR terciles, whatever the current value does to the whole-window terciles."""
    snap = tmp_path / "w" / "snapshots"
    c_captures(snap, r_of=lambda j: {7: 5.0, 8: -5.0}.get(j, 0.1 * j))
    res = cen.pre_census_C(snap)
    c = res["counts"]
    assert c["class_mint"] >= 1 and c["class_merge"] == 1 and c["units_with_6_prior"] == 3  # j = 7 mint, j = 8 merge, j = 9 transfer/mint by its own prior
    assert res["strata"]["levels"]["level2"]["merge_units_reported"] == 1


def test_pre_census_c_gap_edges_dv_zero_closed_member_and_near_end(tmp_path):
    base = tmp_path / "w"
    c_captures(base / "gap99" / "snapshots", n=2, gap_s=99 * 60.0)
    c_captures(base / "gap100" / "snapshots", n=2, gap_s=100 * 60.0)
    c_captures(base / "gap140" / "snapshots", n=2, gap_s=140 * 60.0)
    c_captures(base / "gap141" / "snapshots", n=2, gap_s=141 * 60.0)
    got = {g: cen.pre_census_C(base / g / "snapshots")["counts"] for g in ("gap99", "gap100", "gap140", "gap141")}
    assert got["gap99"].get("intervals", 0) == 0 and got["gap99"]["interval_gap_outside_100_140min"] == 1
    assert got["gap100"]["intervals"] == 1 and got["gap140"]["intervals"] == 1 and got["gap141"]["interval_gap_outside_100_140min"] == 1
    c_captures(base / "dv0" / "snapshots", n=3, dv_zero_at=(1,))
    assert cen.pre_census_C(base / "dv0" / "snapshots")["counts"]["ns_not_traded"] >= 1
    c_captures(base / "closed" / "snapshots", n=4, closed_at=(2,))
    cc = cen.pre_census_C(base / "closed" / "snapshots")["counts"]
    assert cc["excluded_member_closed"] == 2  # a member closed at k excludes intervals k and k+1 (k-1 and k only; nothing later is looked at)
    c_captures(base / "end" / "snapshots", n=3, near_end_at=(1, 2))
    assert cen.pre_census_C(base / "end" / "snapshots")["counts"]["excluded_member_closing_within_3h"] >= 1


def test_pre_census_c_is_deterministic_and_skips_a_post_cutoff_capture(tmp_path):
    snap = tmp_path / "w" / "snapshots"
    c_captures(snap, n=6)
    (snap / "20261016T000000Z_dead0000").mkdir()
    (snap / "20261016T000000Z_dead0000" / "rows.csv.gz").write_bytes(b"not gzip")
    a, b = cen.pre_census_C(snap), cen.pre_census_C(snap)
    assert c17.sha256_obj(a) == c17.sha256_obj(b) and a["input_stats"]["dirs_at_or_after_cutoff_not_opened"] == 1


def test_event_last_page_receipt_is_the_capture_time(tmp_path):
    snap = tmp_path / "snapshots"
    d = write_capture(snap, "2026-10-12T00:00:00Z", [{"mid": "m1", "cid": "c1", "eid": "E1", "bid": "0.5", "ask": "0.52", "oi": "1", "vol": "1"}, {"mid": "m2", "cid": "c2", "eid": "E1", "bid": "0.5", "ask": "0.52", "oi": "1", "vol": "1"}],
                      last_page_offset=90.0)
    st = cen.load_capture_state(d, Counter())
    assert st["T"] == pytest.approx(D12 + 91.0, abs=1.0) and st["ev"]["E1"][0] == 1.0 and set(st["ev"]["E1"][2]) == {"m1", "m2"}


# ---- q0403: cost and lag map -----------------------------------------------------------------------------------------------------------------------


def test_cost_lag_map_cost_bands_receipt_lag_and_enrichment(tmp_path):
    root = tmp_path / "w"
    snap, sw, tr = root / "snapshots", root / "book_sweeps", root / "live_trades"
    write_capture(snap, D12 - 60, [{"mid": "1", "cid": "c1", "eid": "E1", "bid": "0.48", "ask": "0.50"}], name=stamp(D12 + 1.0, "aa01aa01"))
    write_sweep(sw, D12, [{"tok": "A", "mid": "1", "bid": "0.48", "ask": "0.50"}], name=stamp(D12, "00000000"))
    write_sweep(sw, D12 + 120, [{"tok": "A", "mid": "1", "bid": "0.48", "ask": "0.50"}], name=stamp(D12 + 120, "00010000"))  # second sweep of the pass: not used
    write_sweep(sw, D12 + 7200, [{"tok": "A", "mid": "1", "bid": "0.48", "ask": "0.50", "d5a": 100, "d5b": 100}], name=stamp(D12 + 7200, "01000000"))
    write_day(tr, "20261012", [print_(D12 + 60 * k, "c1", 0.5, tx=f"t{k}", recv_lag=400.0 if k else 100000.0) for k in range(10)])
    res = cen.cost_lag_map(sw, snap, tr)
    assert_no_forbidden(res)
    assert res["sweeps"] == {"in_window": 3, "used_first_of_pass": 2}
    k1 = res["cost_c_per_share"]["crypto|P[0.20,0.80]|liq1|1000"]
    assert k1["books"] == 2 and k1["not_executable_within_5c"] == 1 and k1["median"] == pytest.approx(13.97, abs=0.25)  # ask + 5c, bid - 5c, two 4% fees
    k5 = res["cost_c_per_share"]["crypto|P[0.20,0.80]|liq1|5000"]
    assert k5["books"] == 2 and k5["not_executable_within_5c"] == 2 and k5["n"] == 0
    lag = res["receipt_lag_s"]
    assert lag["prints"] == 10 and lag["share_gt_300s"] == 1.0 and lag["share_gt_7200s"] == pytest.approx(0.1, abs=1e-6) and 300 < lag["by_class"]["PATH-SETTLED"]["median"] <= 480
    assert res["enrichment_coverage"]["2026-10-12|prints"] == 10 and res["enrichment_coverage"]["2026-10-12|with_market_id"] == 10


def test_cost_lag_map_reads_recv_ts_and_pre_census_a_does_not(tmp_path):
    w = a_world(tmp_path)
    for p in cen.iter_monitor(w["tr"], Counter(), side=True):
        assert "recv_ts" not in p
    assert "recv_ts" not in json.dumps(run_a(w))


# ---- freeze-check fixes (2026-10-20) ------------------------------------------------------------------------------------------------------------


def test_a_informativeness_is_computed_on_units_in_both_label_cells(tmp_path):
    res = run_a(a_world(tmp_path))
    t = res["strata"]["touch_consistent_T"]
    assert t["units_eligible"] == 22 and t["units_in_both_label_cells"] == 12 and t["levels"]["level2"]["denominator"] == 12 and t["levels"]["level2"]["share"] == 1.0
    assert "units in (market x d) cells holding both labels" in pre.INFORMATIVENESS["binary"]


def test_a_unit_with_a_missing_side_is_non_agreement_in_every_cell(tmp_path):
    res = run_a(a_world(tmp_path, blank_side_first=True))
    assert res["side_agreement"]["overall"] == {"n": 22, "k": 21} and res["fills"]["token_resolution"]["resolved_without_one_side"] == 1
    assert sum(c["n"] - c["k"] for c in res["side_agreement"]["cells"]["class"].values()) == 1


def test_p1_reproduction_flag_and_the_unsigned_print_reader(tmp_path):
    assert pre.p1_reproduction(dict(pre.P1_EXPECTED))["matches"] is True and pre.p1_reproduction(dict(pre.P1_EXPECTED))["flag"] == "P1 REPRODUCED"
    off = pre.p1_reproduction({**pre.P1_EXPECTED, "open": 675})
    assert off["matches"] is False and off["differences"] == {"open": {"expected": 676, "observed": 675}} and "investigate" in off["flag"]
    res = run_a(a_world(tmp_path, zero_size_first=True))
    # a zero-size print still resolves its fill (P1 used condition_id, ts, tx16, outcome_index only) but is not in the side-signed population
    assert res["fills"]["token_resolution"]["resolved"] == 23 and res["input_stats"]["monitor_prints_without_usable_price_or_size"] == 1
    assert res["side_signed_population"]["eligible_units"] == 21 and res["p1_reproduction"]["matches"] is False and res["branch_recorded"] is False


def test_s_touch_never_uses_a_capture_whose_last_page_is_at_or_after_tau(tmp_path):
    res = run_a(a_world(tmp_path, late_wide_capture=False, straddling_wide_capture=True))
    assert res["side_signed_population"]["eligible_units"] == 22 and "touch_wide" not in res["side_signed_population"]["excluded_by_reason"]


def test_first_day_later_group_is_1_to_7_days_only():
    assert [cen.age_bin_first_day(h) for h in (-1.0, 5.9, 23.9, 24.0, 167.9, 168.0)] == ["unknown", "lt6h", "6-24h", "1-7d", "1-7d", "gt7d"]


def test_b_clock_anomaly_units_leave_the_units_and_the_cut_points(tmp_path):
    base = cen.pre_census_B(*[b_world(tmp_path / "ok")[k] for k in ("sw", "snap")])
    an = cen.pre_census_B(*[b_world(tmp_path / "an", anomaly=True)[k] for k in ("sw", "snap")])
    assert an["counts"]["unit_clock_anomaly_or_no_stamp"] == 8 and base["cut_points"]["units"] == 21 and an["cut_points"]["units"] == 14
