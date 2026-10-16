# ruff: noqa: E501
"""CB4 data jobs: closewin/departures extractor (q0080), h7 fetches (q0081/q0082) and seals (q0083)
(astrolabe.research_lab.cb4_data, scripts/run_cb4.py; docs/research_lab/CREATIVE_BATCH_4.md CB4-F)."""

from __future__ import annotations

import gzip
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

from astrolabe.research_lab import cb4_data as d

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import run_cb4 as script  # noqa: E402

ROW_COLS = ["capture_id", "capture_start_utc", "received_utc", "market_id", "condition_id", "event_id", "closed",
            "active", "binary", "best_bid", "best_ask", "spread", "last_trade_price", "chg_1d", "end_date"]
EXT_COLS = ["capture_id", "market_id", "clob_token_id_0", "clob_token_id_1", "accepting_orders", "created_at",
            "uma_resolution_statuses", "volume_num", "fee_schedule", "fee_category", "neg_risk_market_id",
            "series_slugs"]
SW_COLS = ["market_id", "batch_receipt_utc", "state", "best_bid", "best_ask", "bid_size_1", "ask_size_1"]


def _gz(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", newline="") as fh:
        df.to_csv(fh, index=False)


def _row(mid, end, **kw):
    r = dict.fromkeys(ROW_COLS, "")
    r.update(market_id=mid, condition_id=f"c{mid}", event_id=f"E{mid}", closed="False", active="True", binary="1",
             best_bid="0.4000", best_ask="0.4500", spread="0.05", last_trade_price="0.4200", end_date=end,
             received_utc="2026-10-12T00:00:05Z")
    r.update(kw)
    return r


def _ext(mid, created="2026-09-01T00:00:00Z", acc="True", **kw):
    r = dict.fromkeys(EXT_COLS, "")
    r.update(market_id=mid, clob_token_id_0=f"t{mid}a", clob_token_id_1=f"t{mid}b", accepting_orders=acc,
             created_at=created, uma_resolution_statuses="[]", volume_num="100.5", fee_category="crypto",
             neg_risk_market_id="", series_slugs="[]")
    r.update(kw)
    return r


def make_capture(root: Path, cid: str, start: str, rows, ext=None, *, with_files=True) -> Path:
    dd = root / cid
    dd.mkdir(parents=True, exist_ok=True)
    if with_files:
        _gz(dd / "rows.csv.gz", pd.DataFrame(rows, columns=ROW_COLS))
        _gz(dd / "rows_ext.csv.gz", pd.DataFrame(ext if ext is not None else [_ext(r["market_id"]) for r in rows], columns=EXT_COLS))
    (dd / "manifest.json").write_text(json.dumps({"capture_id": cid, "started_utc": start, "state": "complete"}))
    return dd


def make_sweep(root: Path, sid: str, cid: str, k: int, rows) -> None:
    dd = root / sid
    _gz(dd / "rows.csv.gz", pd.DataFrame(rows, columns=SW_COLS))
    (dd / "manifest.json").write_text(json.dumps({"snapshot_id": cid, "series_index": k, "state": "complete",
                                                  "started_utc": f"2026-10-12T00:1{k}:00Z"}))


S0 = "2026-10-12T00:00:00Z"
S1 = "2026-10-12T02:00:00Z"
S2 = "2026-10-12T04:00:00Z"
IN_WIN = "2026-10-12T01:30:00Z"  # inside [start-72h, start+30h]
FAR = "2026-12-01T00:00:00Z"


def _rows_a():
    return [_row("1", IN_WIN), _row("2", FAR), _row("3", FAR), _row("4", IN_WIN), _row("5", "2026-10-12T00:30:00Z")]


def _ext_a():
    return [_ext("1"), _ext("2"), _ext("3", acc="False"),  # 3: far end but order book shut -> kept
            _ext("4", created="2026-10-11T23:00:00Z"),  # 4: life < 1 day -> dropped
            _ext("5", created="")]  # 5: created_at unknown -> kept, counted


# ---- selection --------------------------------------------------------------------------------------------


def test_selection_rules_and_columns(tmp_path):
    snap = tmp_path / "snapshots"
    make_capture(snap, "c0", S0, _rows_a(), _ext_a())
    cap = {"dir": str(snap / "c0")}
    out, listing, facts = d.build_capture(Path(cap["dir"]) / "rows.csv.gz", Path(cap["dir"]) / "rows_ext.csv.gz", None, "c0", S0)
    assert list(out.columns) == d.CLOSEWIN_COLUMNS
    assert list(out["market_id"]) == ["1", "3", "5"]
    assert listing == {"1", "2", "3", "4", "5"}
    assert facts["n_listing"] == 5 and facts["n_rows"] == 3
    assert facts["n_dropped_life_lt_1d"] == 1 and facts["n_life_unknown_kept"] == 1 and facts["n_accepting_false"] == 1
    # raw strings preserved exactly
    r1 = out[out.market_id == "1"].iloc[0]
    assert r1["best_bid"] == "0.4000" and r1["fee_category"] == "crypto" and r1["clob_token_id_1"] == "t1b"
    assert r1["sweep_best_bid"] == "" and facts["sweep_found"] is False


def test_first_receipt_wins_on_duplicates(tmp_path):
    snap = tmp_path / "s"
    make_capture(snap, "c0", S0, [_row("1", IN_WIN, best_bid="0.1000"), _row("1", IN_WIN, best_bid="0.9000")], [_ext("1")])
    out, _l, _f = d.build_capture(snap / "c0" / "rows.csv.gz", snap / "c0" / "rows_ext.csv.gz", None, "c0", S0)
    assert list(out["best_bid"]) == ["0.1000"]


def test_sweep_columns_joined_for_selected_only(tmp_path):
    snap, sw = tmp_path / "s", tmp_path / "sw"
    make_capture(snap, "c0", S0, _rows_a(), _ext_a())
    make_sweep(sw, "sw0", "c0", 0, [{"market_id": "1", "best_bid": "0.41", "best_ask": "0.44", "bid_size_1": "10", "ask_size_1": "11"},
                                    {"market_id": "2", "best_bid": "0.2", "best_ask": "0.3", "bid_size_1": "1", "ask_size_1": "1"}])
    res = d.run_closewin(snap, sw, tmp_path / "root", mode="backfill", since=S0)
    assert res["written"] == 1
    out = d.read_closewin(tmp_path / "root", "c0")
    assert out.loc[out.market_id == "1", "sweep_best_ask"].iloc[0] == "0.44"
    assert (out.loc[out.market_id == "3", "sweep_best_ask"] == "").all()


# ---- driver: idempotence, missing, departures, refusals ------------------------------------------------------


def _three(tmp_path):
    snap = tmp_path / "snapshots"
    make_capture(snap, "c0", S0, _rows_a(), _ext_a())
    # c1 lacks markets 1 and 5 (they left the listing)
    rows1 = [r for r in _rows_a() if r["market_id"] not in ("1", "5")]
    make_capture(snap, "c1", S1, rows1, [e for e in _ext_a() if e["market_id"] in {"2", "3", "4"}])
    make_capture(snap, "c2", S2, [], with_files=False)  # raw gone, no release copy
    return snap


def test_backfill_missing_recorded_and_run_continues_and_idempotent(tmp_path):
    snap = _three(tmp_path)
    root = tmp_path / "root"
    r1 = d.run_closewin(snap, tmp_path / "none", root, mode="backfill", since=S0)
    assert r1["written"] == 2 and r1["missing"] == 1 and r1["remaining"] == 0 and r1["backfill_complete"] is True
    man = json.loads((root / "manifest.json").read_text())
    assert man["captures"]["c2"]["status"] == "missing"
    snaps = {p.name for p in (root / "closewin").glob("*.csv.gz")}
    assert snaps == {"c0.csv.gz", "c1.csv.gz"}
    before = (root / "closewin" / "c0.csv.gz").read_bytes()
    r2 = d.run_closewin(snap, tmp_path / "none", root, mode="backfill", since=S0)
    assert r2["written"] == 0 and r2["missing"] == 0 and r2["backfill_complete"] is True
    assert (root / "closewin" / "c0.csv.gz").read_bytes() == before


def test_departures_from_previous_closewin_and_listing(tmp_path):
    snap = _three(tmp_path)
    root = tmp_path / "root"
    d.run_closewin(snap, tmp_path / "none", root, mode="backfill", since=S0)
    dep = d.read_closewin(root, "c1", departures=True)
    # closewin(c0) = {1,3,5}; c1 listing = {2,3,4}  -> departed: 1 and 5
    assert list(dep.columns) == d.DEPARTURE_COLUMNS
    assert list(dep["market_id"]) == ["1", "5"] and set(dep["last_seen_capture_id"]) == {"c0"}
    man = json.loads((root / "manifest.json").read_text())
    assert man["captures"]["c0"]["departures_status"] == "no_previous_capture"
    assert man["captures"]["c1"]["departures_status"] == "ok"
    assert not (root / "departures" / "c0.csv.gz").exists()


def test_departures_unavailable_when_previous_is_missing(tmp_path):
    snap = tmp_path / "snapshots"
    make_capture(snap, "c0", S0, [], with_files=False)
    make_capture(snap, "c1", S1, _rows_a(), _ext_a())
    root = tmp_path / "root"
    d.run_closewin(snap, tmp_path / "none", root, mode="backfill", since=S0)
    man = json.loads((root / "manifest.json").read_text())
    assert man["captures"]["c1"]["departures_status"] == "previous_closewin_unavailable"


def test_retry_missing_only_when_asked(tmp_path):
    snap = _three(tmp_path)
    root = tmp_path / "root"
    d.run_closewin(snap, tmp_path / "none", root, mode="backfill", since=S0)
    make_capture(snap, "c2", S2, _rows_a(), _ext_a())  # raw now present
    assert d.run_closewin(snap, tmp_path / "none", root, mode="backfill", since=S0)["written"] == 0
    r = d.run_closewin(snap, tmp_path / "none", root, mode="backfill", since=S0, retry_missing=True)
    assert r["written"] == 1


def test_data_dumps_refusal_and_disk_cap_and_budget(tmp_path):
    snap = _three(tmp_path)
    root = tmp_path / "root"
    big = lambda p: 11.0 if Path(p) == tmp_path / "dd" else 0.0  # noqa: E731
    r = d.run_closewin(snap, tmp_path / "none", root, mode="backfill", since=S0, data_dumps=tmp_path / "dd",
                       data_dumps_max_gb=10.5, dir_gb=big)
    assert r["stopped"] == "refused_data_dumps_over_cap" and r["backfill_complete"] is False and r["written"] == 0
    assert not (root / "manifest.json").exists()
    r = d.run_closewin(snap, tmp_path / "none", root, mode="backfill", since=S0, disk_cap_gb=0.0)
    assert r["stopped"] == "disk_cap" and r["backfill_complete"] is False
    ticks = iter(range(0, 1000, 100))
    r = d.run_closewin(snap, tmp_path / "none", root, mode="backfill", since=S0, budget_s=150, clock=lambda: float(next(ticks)))
    assert r["stopped"] == "budget" and r["backfill_complete"] is False


def test_window_bounds_since_before(tmp_path):
    snap = _three(tmp_path)
    r = d.run_closewin(snap, tmp_path / "none", tmp_path / "root", mode="backfill", since=S1, before=S2)
    assert r["written"] == 1 and r["remaining"] == 0


def test_all_new_mode_does_not_report_backfill_complete(tmp_path):
    snap = _three(tmp_path)
    r = d.run_closewin(snap, tmp_path / "none", tmp_path / "root", mode="all-new", since=S0)
    assert r["written"] == 2 and r["backfill_complete"] is False


def test_version_mismatch_refused(tmp_path):
    snap = _three(tmp_path)
    root = tmp_path / "root"
    root.mkdir()
    (root / "manifest.json").write_text(json.dumps({"extractor_version": "other", "captures": {}}))
    with pytest.raises(d.VersionMismatch):
        d.run_closewin(snap, tmp_path / "none", root, mode="backfill", since=S0)


def test_cb1_cb2_tables_untouched_and_only_own_root_written(tmp_path):
    snap = _three(tmp_path)
    cb1, cb2 = tmp_path / "cb1_extract", tmp_path / "cb2_extract"
    cb1.mkdir()
    cb2.mkdir()
    (cb1 / "x.txt").write_text("a")
    (cb2 / "y.txt").write_text("b")
    root = tmp_path / "cb4_extract"
    d.run_closewin(snap, tmp_path / "none", root, mode="backfill", since=S0)
    assert sorted(p.name for p in cb1.iterdir()) == ["x.txt"] and sorted(p.name for p in cb2.iterdir()) == ["y.txt"]
    assert {p.name for p in root.iterdir()} <= {"closewin", "departures", "manifest.json", ".lock"}


# ---- release stream --------------------------------------------------------------------------------------------


def _catalogue(tmp_path, entries):
    cdir = tmp_path / "cat"
    cdir.mkdir(exist_ok=True)
    with open(cdir / "data-test.jsonl", "w") as fh:
        for e in entries:
            fh.write(json.dumps({"release": "data-test", **e}) + "\n")
    return d.Catalogue(cdir)


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def test_release_stream_one_batch_cap_scratch_deleted_and_hash_verified(tmp_path):
    snap = tmp_path / "snapshots"
    for cid, st in (("r0", S0), ("r1", S1), ("r2", S2)):
        make_capture(snap, cid, st, [], with_files=False)
    # the "release": archive-path -> bytes
    src = tmp_path / "release_src"
    src.mkdir()
    entries, blobs = [], {}
    for cid in ("r0", "r1", "r2"):
        rows = _rows_a()
        _gz(src / f"{cid}_rows.csv.gz", pd.DataFrame(rows, columns=ROW_COLS))
        _gz(src / f"{cid}_ext.csv.gz", pd.DataFrame(_ext_a(), columns=EXT_COLS))
        for key, name in (("rows", "rows.csv.gz"), ("ext", "rows_ext.csv.gz")):
            b = (src / f"{cid}_{'rows' if key == 'rows' else 'ext'}.csv.gz").read_bytes()
            ap = f"data-dumps/research_lab/snapshots/{cid}/{name}"
            blobs[ap] = b
            entries.append({"path": ap, "bytes": 90_000_000, "sha256": _sha(b)})
    cat = _catalogue(tmp_path, entries)
    calls, peak = [], []

    def restore(tag, globs, dest):
        calls.append(sorted(globs))
        for g in globs:
            p = Path(dest) / g
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(blobs[g])
        peak.append(sum(f.stat().st_size for f in Path(dest).rglob("*") if f.is_file()))
        return True

    rel = d.ReleaseCopies(tmp_path / "root" / "_scratch", catalogue=cat, restore=restore, cap_bytes=200_000_000)
    r = d.run_closewin(snap, tmp_path / "none", tmp_path / "root", mode="backfill", since=S0, release=rel)
    assert r["written"] == 3 and r["from_release"] == 3 and r["missing"] == 0 and r["backfill_complete"] is True
    # cap 200 MB with 180 MB per capture -> one capture per restore call
    assert len(calls) == 3 and all(len(c) == 2 for c in calls)
    assert not (tmp_path / "root" / "_scratch").exists()
    man = json.loads((tmp_path / "root" / "manifest.json").read_text())
    assert man["captures"]["r1"]["source"] == "release" and man["captures"]["r1"]["departures_status"] == "ok"


def test_release_batches_several_captures_under_cap(tmp_path):
    snap = tmp_path / "snapshots"
    for cid, st in (("r0", S0), ("r1", S1)):
        make_capture(snap, cid, st, [], with_files=False)
    blobs, entries = {}, []
    for cid in ("r0", "r1"):
        for name, df, cols in (("rows.csv.gz", _rows_a(), ROW_COLS), ("rows_ext.csv.gz", _ext_a(), EXT_COLS)):
            p = tmp_path / f"{cid}{name}"
            _gz(p, pd.DataFrame(df, columns=cols))
            ap = f"data-dumps/research_lab/snapshots/{cid}/{name}"
            blobs[ap] = p.read_bytes()
            entries.append({"path": ap, "bytes": 10_000_000, "sha256": _sha(blobs[ap])})
    calls = []

    def restore(tag, globs, dest):
        calls.append(len(globs))
        for g in globs:
            (Path(dest) / g).parent.mkdir(parents=True, exist_ok=True)
            (Path(dest) / g).write_bytes(blobs[g])
        return True

    rel = d.ReleaseCopies(tmp_path / "scr", catalogue=_catalogue(tmp_path, entries), restore=restore)
    r = d.run_closewin(snap, tmp_path / "none", tmp_path / "root", mode="backfill", since=S0, release=rel)
    assert r["written"] == 2 and calls == [4]  # one call restored both captures (80 MB < 0.2 GB)


def test_release_missing_hash_mismatch_and_unknown_are_missing_not_reconstructed(tmp_path):
    snap = tmp_path / "snapshots"
    make_capture(snap, "r0", S0, [], with_files=False)
    make_capture(snap, "r1", S1, [], with_files=False)
    good = tmp_path / "g.csv.gz"
    _gz(good, pd.DataFrame(_rows_a(), columns=ROW_COLS))
    # r0 has a catalogue row but the restored bytes do not match its sha; r1 has no catalogue row at all
    entries = [{"path": f"data-dumps/research_lab/snapshots/r0/{n}", "bytes": 1000, "sha256": "0" * 64} for n in ("rows.csv.gz", "rows_ext.csv.gz")]

    def restore(tag, globs, dest):
        for g in globs:
            (Path(dest) / g).parent.mkdir(parents=True, exist_ok=True)
            (Path(dest) / g).write_bytes(good.read_bytes())
        return True

    rel = d.ReleaseCopies(tmp_path / "scr", catalogue=_catalogue(tmp_path, entries), restore=restore)
    r = d.run_closewin(snap, tmp_path / "none", tmp_path / "root", mode="backfill", since=S0, release=rel)
    assert r["written"] == 0 and r["missing"] == 2 and r["backfill_complete"] is True
    man = json.loads((tmp_path / "root" / "manifest.json").read_text())
    assert {man["captures"][c]["status"] for c in ("r0", "r1")} == {"missing"}


def test_release_restore_failure_twice_stops_not_complete(tmp_path):
    snap = tmp_path / "snapshots"
    for cid, st in (("r0", S0), ("r1", S1), ("r2", S2)):
        make_capture(snap, cid, st, [], with_files=False)
    entries = [{"path": f"data-dumps/research_lab/snapshots/{c}/{n}", "bytes": 1000, "sha256": None}
               for c in ("r0", "r1", "r2") for n in ("rows.csv.gz", "rows_ext.csv.gz")]
    rel = d.ReleaseCopies(tmp_path / "scr", catalogue=_catalogue(tmp_path, entries), restore=lambda *_a: False, cap_bytes=2500)
    r = d.run_closewin(snap, tmp_path / "none", tmp_path / "root", mode="backfill", since=S0, release=rel)
    assert r["stopped"] == "release_unavailable" and r["backfill_complete"] is False


def test_release_capture_larger_than_scratch_cap_is_not_restored(tmp_path):
    snap = tmp_path / "snapshots"
    make_capture(snap, "r0", S0, [], with_files=False)
    entries = [{"path": f"data-dumps/research_lab/snapshots/r0/{n}", "bytes": 150_000_000, "sha256": None} for n in ("rows.csv.gz", "rows_ext.csv.gz")]
    called = []
    rel = d.ReleaseCopies(tmp_path / "scr", catalogue=_catalogue(tmp_path, entries), restore=lambda *_a: called.append(1) or True)
    r = d.run_closewin(snap, tmp_path / "none", tmp_path / "root", mode="backfill", since=S0, release=rel)
    assert r["missing"] == 1 and not called


# ---- script ----------------------------------------------------------------------------------------------------


def test_script_closewin_exit_codes_and_complete_flag(tmp_path, capsys):
    snap = _three(tmp_path)
    base = ["closewin", "--backfill-from", S0, "--snapshot-root", str(snap), "--sweep-root", str(tmp_path / "none"),
            "--root", str(tmp_path / "root"), "--data-dumps", str(tmp_path), "--data-dumps-max-gb", "10.5"]
    assert script.main(base) == 0
    out = capsys.readouterr().out
    assert '"backfill_complete": true' in out
    # refusal: data-dumps over the cap -> non-zero and the flag is false
    assert script.main([*base[:-1], "0.0"]) == 1
    out = capsys.readouterr().out
    assert '"backfill_complete": true' not in out and "refused_data_dumps_over_cap" in out


def test_script_analysis_hook_exits_2_when_module_absent():
    assert script.main(["census"]) == 2
