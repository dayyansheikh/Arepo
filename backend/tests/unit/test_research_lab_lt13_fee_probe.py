# ruff: noqa: E501
"""q0717 LT13 fee-reading probe: synthetic captures only (no data-dumps reads)."""

from __future__ import annotations

import csv
import gzip
import importlib.util
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from astrolabe.research_lab import lt13_fee_probe as m
from astrolabe.research_lab import population_map_ch251 as c251
from astrolabe.research_lab import population_map_ch261 as c261

_P = Path(__file__).resolve().parents[2] / "scripts" / "run_lt13_fee_probe.py"
_spec = importlib.util.spec_from_file_location("run_lt13_fee_probe_under_test", _P)
runner = importlib.util.module_from_spec(_spec)
sys.modules["run_lt13_fee_probe_under_test"] = runner
_spec.loader.exec_module(runner)

T0 = datetime(2026, 10, 16, 0, 31, tzinfo=UTC)
RCOLS = ["market_id", "event_id", "received_utc", "closed", "active", "binary", "best_bid", "best_ask", "neg_risk", "liquidity"]
ECOLS = ["market_id", "fee_type", "fee_category", "series_slugs", "clob_rewards", "order_price_min_tick_size", "volume_num", "fees_enabled", "fee_schedule", "created_at",
         "accepting_orders", "uma_resolution_statuses", "event_comment_count", "event_volume", "taker_base_fee", "future_trap_column"]
FEE_ON = '{"exponent":1,"rate":0.05,"rebateRate":0.25,"takerOnly":true}'
FEE_0 = '{"exponent":1,"rate":0,"rebateRate":0,"takerOnly":true}'
ELIG = "nonsports_excrypto"


def mk(mid, bid=0.49, ask=0.51, rw="", fs=FEE_ON, fe="True", ft="politics_v1", fc="politics", tbf="1000", created="2026-05-01T00:00:00Z", closed="false", side=True):
    rec = T0.strftime("%Y-%m-%dT%H:%M:%SZ")
    row = {"market_id": mid, "event_id": "e" + mid, "received_utc": rec, "closed": closed, "active": "true", "binary": "true", "best_bid": f"{bid:.4f}", "best_ask": f"{ask:.4f}",
           "neg_risk": "false", "liquidity": "1000"}
    ext = None if not side else {"market_id": mid, "fee_type": ft, "fee_category": fc, "series_slugs": "", "clob_rewards": rw, "order_price_min_tick_size": "0.01", "volume_num": "5",
                                 "fees_enabled": fe, "fee_schedule": fs, "created_at": created, "accepting_orders": "true", "uma_resolution_statuses": "", "event_comment_count": "",
                                 "event_volume": "", "taker_base_fee": tbf, "future_trap_column": "NEVER"}
    return row, ext


def one_sided(mid, **kw):
    return mk(mid, bid=0.0, ask=0.5, **kw)


def write_cap(root: Path, k: int, items, hours=None, ecols=ECOLS, ext_version="snapshot-ext-v3", with_rows=True):
    t = T0 + timedelta(hours=2 * k if hours is None else hours)
    d = root / f"cap{k:03d}"
    d.mkdir(parents=True)
    (d / "manifest.json").write_text(json.dumps({"state": "complete", "started_utc": t.strftime("%Y-%m-%dT%H:%M:%SZ")}))
    (d / "ext_manifest.json").write_text(json.dumps({"ext_version": ext_version}))
    files = (("rows.csv.gz", RCOLS, 0), ("rows_ext.csv.gz", ecols, 1)) if with_rows else ()
    for name, cols, idx in files:
        with gzip.open(d / name, "wt", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for it in items:
                if it[idx] is not None:
                    w.writerow(it[idx])
    return d


def span(hours=24):
    return "2026-10-16T00:00:00Z", (T0 - timedelta(minutes=31) + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")


def base_items(k):
    return [
        mk("A", fe="false"),  # fee-free by the flag (schedule ignored), complete
        (one_sided if k == 0 else mk)("B", fs=FEE_0),  # fee-free by rate 0, two-sided only at k = 1
        mk("C"),  # fee-on, complete
        mk("D", fe="", fs="", tbf=""),  # unknown (no schedule)
        mk("E", rw='[{"rate":1}]'),  # rewarded fee-on
        mk("F", side=False),  # no sidecar row
        mk("G", ft="", fc="unknown", fe="false"),  # missing feeType: the literal 'unknown' category is non-crypto in the maps
        mk("S", ft="sports_fees_v2", fc="sports"),
        mk("X", closed="true"),  # not an open row
    ]


def test_cells_classes_and_headline(tmp_path):
    write_cap(tmp_path, 0, base_items(0))
    write_cap(tmp_path, 1, base_items(1))
    res = m.run_probe([tmp_path], *span())
    p0, p1 = res["per_capture"]
    assert p0["open_binary_rows"] == 8 and p0["rows_with_sidecar_row"] == 7 and not p0["has_previous_capture"] and p1["has_previous_capture"]
    c = p1["counts"]
    assert c[f"ch251_open_row|{ELIG}|unrewarded|fee_free|flag_off"] == 2  # A and G
    assert c[f"ch251_open_row|{ELIG}|unrewarded|fee_free|rate_zero"] == 1  # B
    assert c[f"ch261_complete_unit|{ELIG}|unrewarded|fee_free|flag_off"] == 2
    assert f"ch261_complete_unit|{ELIG}|unrewarded|fee_free|rate_zero" not in c  # B one-sided at k - 1
    assert c[f"ch261_complete_unit|{ELIG}|unrewarded|fee_on|rate_pos"] == 1
    assert c[f"ch251_open_row|{ELIG}|unrewarded|unknown|no_schedule"] == 1
    assert c[f"ch251_open_row|{ELIG}|rewarded|fee_on|rate_pos"] == 1
    assert c["ch251_open_row|unknown|unknown|unknown|no_sidecar"] == 1
    assert c["ch251_open_row|sports|unrewarded|fee_on|rate_pos"] == 1
    assert not any(k.startswith("ch261_complete_unit") for k in p0["counts"])
    h = res["headline_nonsports_excrypto_unrewarded"]
    assert h["ch251_def_fee_free_unrewarded_open_rows"]["all_covered"]["n_captures"] == 2
    assert h["ch251_def_fee_free_unrewarded_open_rows"]["all_covered"]["total"] == 6  # 3 a capture
    assert h["ch261_def_fee_free_unrewarded_complete_units"]["all_covered"] == {**h["ch261_def_fee_free_unrewarded_complete_units"]["all_covered"], "n_captures": 1, "total": 2.0}
    assert h["ch261_def_fee_on_unrewarded_complete_units"]["by_date_mean"] == {"2026-10-16": 1.0}
    raw = p1["raw_fields_eligible_and_unknown"]
    assert raw[f"ch261_complete_unit|{ELIG}|unrewarded|fee_free|flag_off|fe=false|fs=rate_pos|tbf=pos|age=post_0330"] == 2
    assert raw[f"ch251_open_row|{ELIG}|unrewarded|unknown|no_schedule|fe=blank|fs=empty|tbf=blank|age=post_0330"] == 1
    assert raw["ch251_open_row|unknown|unknown|unknown|no_sidecar|fe=no_sidecar_row|fs=no_sidecar_row|tbf=no_sidecar_row|age=age_na"] == 1
    ft = res["by_date_fee_type_and_fee_category"]["2026-10-16"]
    assert ft[f"ch251_open_row|{ELIG}|fee_free|ft=<blank>|fc=unknown"] == 2  # G at both captures
    assert set(res["fee_schedule_texts_by_hash"].values()) == {FEE_ON, FEE_0}
    assert res["captures"]["covered"] == 2 and res["captures"]["covered_span"]["first_start_utc"] == "2026-10-16T00:31:00Z"


def test_cell_reading_equals_the_ch261_map_reader(tmp_path):
    d = write_cap(tmp_path, 0, base_items(1))
    rows = c251.read_rows(d / "rows.csv.gz")
    ours, has, _t = m.read_ext_states(d / "rows_ext.csv.gz", set(rows), m._Bucket(), m._Bucket())
    theirs = c261.read_ext(d / "rows_ext.csv.gz", set(rows))
    assert set(ours) == set(theirs) and has["taker_base_fee"]
    for mid, x in theirs.items():
        cat, rw, _tick, _vol, fee, src = x[:6]
        assert ours[mid][:4] == (cat, rw, fee, src)


def test_raw_field_states_and_buckets(monkeypatch):
    assert [m.fe_state(True, v) for v in ("True", "false", "", " 0 ", "maybe")] == ["true", "false", "blank", "false", "other"]
    assert m.fe_state(False, "true") == "col_absent"
    assert m.fs_state(True, FEE_ON)[0] == "rate_pos" and m.fs_state(True, FEE_0)[0] == "rate_zero"
    assert m.fs_state(True, "")[0] == "empty" and m.fs_state(True, "{bad")[0] == "unparseable"
    assert m.fs_state(True, '{"x":1}')[0] == "no_rate_key" and m.fs_state(True, '{"rate":"NaN"}')[0] == "rate_nonnumeric"
    assert m.fs_state(False, FEE_ON) == ("col_absent", "-") and len(m.fs_state(True, FEE_ON)[1]) == 16
    assert [m.tbf_state(True, v) for v in ("", "0", "1000", "x", "-1")] == ["blank", "zero", "pos", "other", "other"]
    assert m.age_class("2026-01-01T00:00:00Z") == "pre_0330" and m.age_class("") == "age_na"
    monkeypatch.setattr(m, "MAX_DISTINCT", 2)
    b = m._Bucket()
    assert [b(v) for v in ("a", "b", "c", "a", "", None)] == ["a", "b", "<other>", "a", "<blank>", "<blank>"]


def test_fee_and_category_switches_against_km1(tmp_path):
    write_cap(tmp_path, 0, [mk("A", fs=FEE_0), mk("B")])
    write_cap(tmp_path, 1, [mk("A"), mk("B", ft="crypto_x", fc="crypto")])
    res = m.run_probe([tmp_path], *span())
    sw = res["per_capture"][1]["fee_or_category_class_changes_vs_km1"]
    assert sw == {f"fee fee_free->fee_on|cat {ELIG}->{ELIG}": 1, f"fee fee_on->fee_on|cat {ELIG}->crypto": 1}
    assert res["by_date_class_changes_vs_km1"]["2026-10-16"] == sw


def test_rows_gone_counted_missing_never_restored_and_span_printed(tmp_path):
    write_cap(tmp_path, 0, base_items(0))
    write_cap(tmp_path, 1, base_items(1), with_rows=False)  # rows file deleted by retention
    write_cap(tmp_path, 2, base_items(1))
    res = m.run_probe([tmp_path], *span())
    c = res["captures"]
    assert c["covered"] == 2 and [g["id"] for g in c["rows_gone_counted_missing_never_restored"]] == ["cap001"]
    assert c["missing_expected"] == 10 and res["per_capture"][1]["has_previous_capture"] is False
    assert c["covered_span"] == {"first_start_utc": "2026-10-16T00:31:00Z", "last_start_utc": "2026-10-16T04:31:00Z"}
    assert not any("cap001" in i["path"] for i in res["inputs"])
    lines = runner.summary_lines(res)
    assert "covered 2 of 12 slots" in lines[0] and "rows gone (missing, not restored) 1" in lines[0]


def test_no_capture_k_plus_one_is_read_or_used(tmp_path, monkeypatch):
    a, bdir = tmp_path / "a", tmp_path / "b"
    for root, last in ((a, [mk("A", fe="false"), mk("Z", fs=FEE_0)]), (bdir, [one_sided("A"), mk("C", rw="x")])):
        write_cap(root, 0, base_items(0))
        write_cap(root, 1, base_items(1))
        write_cap(root, 2, last)
    ra, rb = m.run_probe([a], *span()), m.run_probe([bdir], *span())
    assert ra["per_capture"][:2] == rb["per_capture"][:2]  # capture k's counts never depend on capture k + 1
    assert ra["per_capture"][2] != rb["per_capture"][2]
    end = (T0 + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    seen = []
    orig_r, orig_e = c251.read_rows, m.read_ext_states
    monkeypatch.setattr(c251, "read_rows", lambda p: (seen.append(p.parent.name), orig_r(p))[1])
    monkeypatch.setattr(m, "read_ext_states", lambda p, keep, x, y: (seen.append(p.parent.name), orig_e(p, keep, x, y))[1])
    ra, rb = m.run_probe([a], "2026-10-16T00:00:00Z", end), m.run_probe([bdir], "2026-10-16T00:00:00Z", end)
    assert set(seen) == {"cap000", "cap001"}
    drop = ("inputs", "code_sha256", "peak_rss_mb")
    assert {k: v for k, v in ra.items() if k not in drop} == {k: v for k, v in rb.items() if k not in drop}
    assert "future_trap_column" not in m.EXT_COLS and "volume_num" not in m.EXT_COLS and "best_bid" not in m.EXT_COLS


def test_inputs_hashed_ext_version_and_column_absence(tmp_path):
    write_cap(tmp_path, 0, base_items(0), ecols=[c for c in ECOLS if c not in ("fees_enabled", "taker_base_fee")], ext_version="snapshot-ext-v2")
    res = m.run_probe([tmp_path], *span())
    assert len(res["inputs"]) == 4 and all(len(i["sha256"]) == 64 and i["bytes"] > 0 for i in res["inputs"])
    assert set(res["code_sha256"]) == {"lt13_fee_probe.py", "run_lt13_fee_probe.py"}
    p = res["per_capture"][0]
    assert p["ext_version"] == "snapshot-ext-v2" and p["sidecar_columns_present"]["fees_enabled"] is False
    assert p["counts"][f"ch251_open_row|{ELIG}|unrewarded|fee_on|rate_pos"] == 3  # A's false flag unread without the column: rate decides
    assert any("fe=col_absent" in k and "tbf=col_absent" in k for k in p["raw_fields_eligible_and_unknown"])


def test_runner_guards_refuse_paths_overwrite_and_caps(tmp_path, monkeypatch, capsys):
    snap = tmp_path / "research_lab" / "snapshots"
    write_cap(snap, 0, base_items(0))
    write_cap(snap, 1, base_items(1))
    out = tmp_path / "research_lab" / "o" / "p.json"
    args = ["--snapshot-root", str(snap), "--start-utc", "2026-10-16T00:00:00Z", "--end-utc", "2026-10-17T00:00:00Z", "--out", str(out)]
    assert runner.main(args) == 0 and out.exists()
    printed = capsys.readouterr().out
    assert "first 2026-10-16T00:31:00Z" in printed and "ch261_def_fee_free_unrewarded_complete_units: mean 2.0" in printed
    assert json.loads(out.read_text())["version"] == m.VERSION
    assert runner.main(args) == 1
    bad_root = tmp_path / "elsewhere"
    write_cap(bad_root, 0, base_items(0))
    assert runner.main([*args[:1], str(bad_root), *args[2:-1], str(tmp_path / "research_lab" / "o" / "x.json")]) == 2
    assert runner.main([*args[:-1], str(tmp_path / "outside" / "x.json")]) == 2
    out2 = tmp_path / "research_lab" / "o" / "p2.json"
    monkeypatch.setattr(runner, "_above_cap", lambda gb: True)
    assert runner.main([*args[:-1], str(out2), "--data-dumps-cap-gb", "50"]) == 75
    assert not out2.exists()
    monkeypatch.setattr(runner, "_above_cap", lambda gb: False)
    assert runner.main([*args[:-1], str(out2), "--min-free-gb", "1e9"]) == 75
