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


def _ext(mid, created="2026-09-01T00:00:00Z", acc="1", **kw):
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
    return [_ext("1"), _ext("2"), _ext("3", acc="0"),  # 3: far end but order book shut (sidecar writes 1/0) -> kept
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


def test_accepting_orders_flag_formats_and_ext_present(tmp_path):
    from astrolabe.research_lab.extract import _flag  # noqa: PLC0415

    assert _flag(True) == 1 and _flag(False) == 0
    for v in ("0", "0.0", "False", "false", " FALSE "):
        assert d.flag_off(v)
    for v in ("1", "True", "", "1.0"):
        assert not d.flag_off(v)
    snap = tmp_path / "s"
    rows = [_row("1", FAR), _row("2", FAR), _row("3", FAR), _row("4", FAR)]
    ext = [_ext("1", acc="0"), _ext("2", acc="False"), _ext("3", acc="1")]  # market 4 has no sidecar row
    make_capture(snap, "c0", S0, rows, ext)
    (snap / "c0" / "ext_manifest.json").write_text(json.dumps({"ext_version": "snapshot-ext-v3", "sidecar_status": "complete"}))
    out, _l, facts = d.build_capture(snap / "c0" / "rows.csv.gz", snap / "c0" / "rows_ext.csv.gz", None, "c0", S0)
    assert list(out["market_id"]) == ["1", "2"] and list(out["ext_present"]) == ["1", "1"]
    assert facts["n_rows_without_sidecar"] == 1 and facts["n_selected_without_sidecar"] == 0
    assert facts["ext_version"] == "snapshot-ext-v3" and facts["sidecar_status"] == "complete"


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


def test_data_dumps_refusal_only_on_real_headroom(tmp_path):
    snap = _three(tmp_path)
    at = lambda gb: (lambda p: gb if Path(p) == tmp_path / "dd" else 0.0)  # noqa: E731
    # 10.9 GB + 0.4 GB output allowance <= 12: runs (the old 10.5 GB rule would have deadlocked here)
    r = d.run_closewin(snap, tmp_path / "none", tmp_path / "r1", mode="backfill", since=S0, data_dumps=tmp_path / "dd",
                       data_dumps_max_gb=12.0, dir_gb=at(10.9))
    assert r["written"] == 2 and r["backfill_complete"] is True
    # with the 0.2 GB scratch (release stream) 11.5 + 0.4 + 0.2 > 12: refused
    rel = d.ReleaseCopies(tmp_path / "scr", catalogue=d.Catalogue(tmp_path / "nocat"))
    r = d.run_closewin(snap, tmp_path / "none", tmp_path / "r2", mode="backfill", since=S0, data_dumps=tmp_path / "dd",
                       data_dumps_max_gb=12.0, dir_gb=at(11.5), release=rel)
    assert r["stopped"] == "refused_data_dumps_over_cap"
    r = d.run_closewin(snap, tmp_path / "none", tmp_path / "r3", mode="backfill", since=S0, data_dumps=tmp_path / "dd",
                       data_dumps_max_gb=12.0, dir_gb=at(11.7))
    assert r["stopped"] == "refused_data_dumps_over_cap"


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
    cdir.mkdir(parents=True, exist_ok=True)
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
    assert man["captures"]["r0"]["reason"] == "release_hash_mismatch" and man["captures"]["r1"]["reason"] == "no_release_copy"


def test_release_restore_failure_after_retries_stops_not_complete(tmp_path):
    snap = tmp_path / "snapshots"
    for cid, st in (("r0", S0), ("r1", S1), ("r2", S2)):
        make_capture(snap, cid, st, [], with_files=False)
    entries = [{"path": f"data-dumps/research_lab/snapshots/{c}/{n}", "bytes": 1000, "sha256": None}
               for c in ("r0", "r1", "r2") for n in ("rows.csv.gz", "rows_ext.csv.gz")]
    rel = d.ReleaseCopies(tmp_path / "scr", catalogue=_catalogue(tmp_path, entries), restore=lambda *_a: False, cap_bytes=2500, retries=2, backoff_s=0, sleep=lambda s: None)
    r = d.run_closewin(snap, tmp_path / "none", tmp_path / "root", mode="backfill", since=S0, release=rel)
    assert r["stopped"] == "release_unavailable" and r["backfill_complete"] is False
    # transient failure: nothing is marked missing, the capture stays pending (order and departures preserved)
    assert r["missing"] == 0 and r["remaining"] == 3 and r["restore_retries"] == 2


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


def _hide_analysis(monkeypatch):
    """Simulate cb4_analysis being absent (it exists now; a real census/pilot would read data or use the network)."""
    import astrolabe.research_lab as rl  # noqa: PLC0415

    monkeypatch.delattr(rl, "cb4_analysis", raising=False)
    monkeypatch.setitem(sys.modules, "astrolabe.research_lab.cb4_analysis", None)


def test_script_analysis_hook_exits_2_when_module_absent(monkeypatch):
    _hide_analysis(monkeypatch)
    assert script.main(["census"]) == 2


# =====================================================================================================
# h7 fetches (q0081, q0082) and seals (q0083)
# =====================================================================================================

import types  # noqa: E402
from datetime import UTC, datetime  # noqa: E402

from astrolabe.research_lab import h5_seal  # noqa: E402

KEY = b"k" * 32
BIG = 10**12


def ep(s: str) -> float:
    return d._ep(s)


def iso(t: float) -> str:
    return d._iso(t)


def gmarket(mid, end, *, fee="crypto", created="2026-02-01T00:00:00Z", closed=True, title="Will X happen?", prices='["1","0"]',
            outcomes='["Yes","No"]', group=None, closed_time=None, event_id=None, event_title="Event"):
    return {"id": str(mid), "conditionId": f"0xc{mid}", "clobTokenIds": json.dumps([f"t{mid}a", f"t{mid}b"]), "feeType": fee,
            "createdAt": created, "startDate": created, "endDate": end, "closed": closed, "closedTime": closed_time or "",
            "outcomePrices": prices, "outcomes": outcomes, "question": title, "groupItemTitle": group, "negRisk": False,
            "umaResolutionStatus": "resolved", "volumeNum": 123.0, "liquidityNum": 4.0,
            "events": [{"id": event_id or f"E{mid}", "title": event_title}]}


class FakeNet:
    """Offline Gamma / CLOB / Data API."""

    def __init__(self, markets=(), events=(), series_ok=False, trades_after=()):
        self.markets, self.events, self.series_ok = list(markets), list(events), series_ok
        self.price_calls: list[str] = []
        self.trade_calls: list[str] = []
        self.requests = 0
        self.trades_after = list(trades_after)
        self.fail_price_tokens: set[str] = set()
        self.fail_trades = False
        self.fail_markets = False

    @staticmethod
    def _in(win_lo, win_hi, end):
        return win_lo <= d._parse_ts(end) <= win_hi

    def __call__(self, url, params):
        self.requests += 1
        if url.endswith("/markets"):
            if self.fail_markets:
                return 404, b"{}", {}
            lo, hi = ep(params["end_date_min"]), ep(params["end_date_max"])
            want = params["closed"] == "true"
            rows = [m for m in self.markets if bool(m["closed"]) == want and lo <= d._parse_ts(m["endDate"]) < hi]
            return 200, json.dumps(rows[params["offset"]: params["offset"] + params["limit"]]).encode(), {}
        if url.endswith("/events"):
            lo, hi = ep(params["end_date_min"]), ep(params["end_date_max"])
            want = params["closed"] == "true"
            rows = [e for e in self.events if bool(e.get("closed")) == want and lo <= d._parse_ts(e["endDate"]) < hi]
            return 200, json.dumps(rows[params["offset"]: params["offset"] + params["limit"]]).encode(), {}
        if url.endswith("/series"):
            if self.series_ok:
                return 200, json.dumps([{"id": "S1", "slug": "s", "title": "t", "closed": False, "outcomePrices": "x"}]).encode(), {}
            return 404, b"{}", {}
        if url.endswith("/prices-history"):
            self.price_calls.append(params["market"])
            if params["market"] in self.fail_price_tokens:
                return 404, b"{}", {}
            a, b = params["startTs"], params["endTs"]
            return 200, json.dumps({"history": [{"t": a + 600 * k, "p": 0.5} for k in range(1, 4) if a + 600 * k < b]}).encode(), {}
        if url.endswith("/trades"):
            self.trade_calls.append(params["market"])
            if self.fail_trades:
                return 404, b"{}", {}
            if params["offset"] > 0:
                return 200, b"[]", {}
            base = int(ep("2026-03-02"))
            tr = [{"timestamp": base + 100 * k, "side": "BUY", "size": 10, "price": 0.5, "outcomeIndex": 0, "asset": "a",
                   "transactionHash": f"h{params['market']}{k}", "proxyWallet": f"0xw{k}"} for k in range(3)]
            tr += [{"timestamp": int(t), "side": "SELL", "size": 5, "price": 0.4, "outcomeIndex": 1, "asset": "a",
                    "transactionHash": f"late{params['market']}{t}", "proxyWallet": "0xz"} for t in self.trades_after]
            return 200, json.dumps(tr).encode(), {}
        return 404, b"{}", {}


def _ns(**kw):
    base = dict(kind="era", run_id=None, seed=None, per_cell=None, periods=None, origin_window_h=None, min_life_d=None,
                n_series=None, n_sports_series=None, members_per_series=None, roll_from=None, exclude_runs="",
                exclude_seal_ids="", exclude_categories="weather", walk_closed="true,false", cap_at=d.T_SEAL, rps=4.0,
                disk_cap_gb=None, budget_min=None, max_trades=None, root=None, data_dumps=None, data_dumps_cap_gb=10.0,
                snapshot_root=None, series_rules_file=None, key=KEY, sleep=lambda s: None, live_check=lambda: False,
                health_check=lambda t: (True, "ok"))
    base.update(kw)
    return types.SimpleNamespace(**base)


def _h5_copy(tmp_path, ids=("999",)):
    p = tmp_path / "seals" / "h5_cb1_SEAL.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"run_id": "h5_cb1", "files": {f"prices/{i}.csv.gz": "x" for i in ids}}))
    (p.parent / "h5_cb1_ladders_SEAL.json").write_text(json.dumps({"run_id": "h5_cb1_ladders", "files": {"prices/L777.csv.gz": "x"}}))
    return p


NOW = ep("2026-03-20")


def _wall(t=NOW):
    return lambda: t


# ---- pure rules ---------------------------------------------------------------------------------------------


def test_parse_periods_and_days():
    ps = d.parse_periods(d.ERA_PERIODS)
    assert [p[0] for p in ps] == ["P0", "P1", "P2"] and len(d.era_days(ps)) == 79 + 33 + 22
    assert d.era_period_of(ep("2026-02-20"), ps) is None and d.era_period_of(ep("2026-03-01"), ps) == "P1"


def test_cadence_classes():
    day = 86400.0
    assert d.cadence_class([i * day for i in range(5)]) == "daily"
    assert d.cadence_class([i * 7 * day for i in range(5)]) == "weekly"
    assert d.cadence_class([i * 30 * day for i in range(5)]) == "monthly"
    assert d.cadence_class([i * 3600.0 for i in range(10)]) is None  # sub-daily
    assert d.cadence_class([0, 3 * day, 4 * day, 9 * day]) is None and d.cadence_class([5.0]) is None


def test_winner_binary_and_multi_and_void():
    def pred(markets):
        return {"markets": markets}

    m1 = {"market_id": "1", "outcomes": ["Up", "Down"], "group_title": None}
    g = lambda prices, closed=True, ct="2026-03-02T10:00:00Z": {"markets": [{"market_id": "1", "outcome_prices": prices, "closed": closed, "closed_time": ct}]}  # noqa: E731
    assert d.winner_of(pred([m1]), g('["0","1"]'))[0] == "down"
    assert d.winner_of(pred([m1]), g('["0.5","0.5"]')) is None  # 50-50
    assert d.winner_of(pred([m1]), g('["1","0"]', closed=False)) is None
    assert d.winner_of(pred([m1]), g('["1","0"]', ct="")) is None
    ma = {"market_id": "A", "outcomes": ["Yes", "No"], "group_title": "Alice B."}
    mb = {"market_id": "B", "outcomes": ["Yes", "No"], "group_title": "Bob"}
    mk = lambda a, b: {"markets": [{"market_id": "A", "outcome_prices": a, "closed": True, "closed_time": "2026-03-02T10:00:00Z"}, {"market_id": "B", "outcome_prices": b, "closed": True, "closed_time": "2026-03-02T10:05:00Z"}]}  # noqa: E731
    k, t0, lab = d.winner_of(pred([ma, mb]), mk('["0","1"]', '["1","0"]'))
    assert k == "bob" and lab is None and t0 == ep("2026-03-02T10:05:00Z")  # t0 is the WINNING market's closedTime
    assert d.winner_of(pred([ma, mb]), mk('["1","0"]', '["1","0"]')) is None  # two winners
    assert d.winner_of(pred([ma, mb]), mk('["0","1"]', '["0","1"]')) is None  # no winner


def test_match_side_binary_multi_and_mismatch():
    pred1 = {"markets": [{"outcomes": ["Up", "Down"]}]}
    succ1 = {"markets": [{"market_id": "9", "outcomes": ["Down", "Up"], "group_title": None}]}
    assert d.match_side(succ1, pred1, "up") == ("9", 1)
    assert d.match_side(succ1, pred1, "sideways") is None
    predm = {"markets": [{}, {}]}
    succm = {"markets": [{"market_id": "A", "group_title": "Alice  B."}, {"market_id": "B", "group_title": "Bob"}]}
    assert d.match_side(succm, predm, "alice b") == ("A", 0)
    assert d.match_side(succm, predm, "carol") is None  # no exact match -> excluded
    assert d.match_side(succm, pred1, "up") is None  # structure mismatch


def test_pick_successor_created_lag_and_skip():
    ms = [{"end_epoch": 100.0, "created_epoch": 0.0}, {"end_epoch": 200.0, "created_epoch": 10_000.0},
          {"end_epoch": 300.0, "created_epoch": 50.0}]
    j, skipped = d.pick_successor(ms, 0, t0=10_000.0)  # next member created after t0 - 1h: skipped
    assert j == 2 and skipped is True
    ms[1]["created_epoch"] = 100.0
    assert d.pick_successor(ms, 0, t0=7200.0) == (1, False)
    assert d.pick_successor(ms, 2, t0=7200.0) == (None, False)


def test_split_h7s_rule_embargo_and_deterministic():
    units = [{"unit_id": f"u{i}", "t0_epoch": ep("2026-03-01") + i * 86400.0} for i in range(10)]  # one per day
    sp = d.split_h7s(units)
    assert sp["d_split4"] == "2026-03-07"  # 4 units at or after = 40%
    assert sp["holdout"] == ["u6", "u7", "u8", "u9"] and sp["embargo"] == ["u3", "u4", "u5"]
    assert sp["screen"] == ["u0", "u1", "u2"]
    assert d.split_h7s(list(reversed(units))) == sp
    assert d.split_h7s([])["n"] == 0


def test_apply_era_rules_each_counted():
    ps = [("P0", ep("2026-03-01"), ep("2026-03-10"))]
    base = dict(condition_id="c", token0="a", token1="b", event_id="e", start_at="", start_epoch=0.0, neg_risk=0, weather_title=0,
                fee_category="crypto", created_at="2026-02-01T00:00:00Z", end_at="")
    mk = lambda mid, end, **kw: {**base, "market_id": mid, "end_epoch": ep(end), **kw}  # noqa: E731
    rows = [mk("ok", "2026-03-08T00:00:00Z"), mk("sp", "2026-03-08T00:00:00Z", fee_category="sports"),
            mk("wx", "2026-03-08T00:00:00Z", fee_category="weather"), mk("wt", "2026-03-08T00:00:00Z", weather_title=1),
            mk("h", "2026-03-08T00:00:00Z"), mk("h5", "2026-03-08T00:00:00Z"), mk("out", "2026-04-08T00:00:00Z"),
            mk("short", "2026-03-08T00:00:00Z", created_at="2026-03-06T00:00:00Z"),
            mk("nocr", "2026-03-08T00:00:00Z", created_at=""), mk("early", "2026-03-02T00:00:00Z"),
            {**mk("noend", "2026-03-08T00:00:00Z"), "end_epoch": float("nan")}]
    kept, c = d.apply_era_rules(rows, ps, history_ids={"h"}, h5_ids={"h5"}, sports_cats=("sports",))
    assert {r["market_id"] for r in kept} == {"ok", "sp"} and {r["group"] for r in kept} == {"O", "S"}
    assert c["weather"] == 2 and c["history_sample_overlap"] == 1 and c["h5_overlap"] == 1 and c["outside_periods"] == 1
    assert c["life_lt_min"] == 1 and c["life_unknown"] == 1 and c["origin_window_outside_period"] == 1 and c["no_end_date"] == 1


def test_draw_era_sample_cells_and_determinism():
    rows = [{"market_id": str(i), "group": "S" if i % 2 else "O", "period": "P0", "fee_category": "crypto" if i % 3 else "politics",
             "created_at": f"2026-0{1 + i % 2}-05T00:00:00Z"} for i in range(60)]
    s1, rep = d.draw_era_sample(rows, 10, "seed")
    s2, _ = d.draw_era_sample(list(reversed(rows)), 10, "seed")
    assert {r["market_id"] for r in s1} == {r["market_id"] for r in s2} and len(s1) == 20
    assert rep["cells"]["O|P0"]["sampled"] == 10 and rep["cells"]["S|P0"]["shortfall"] == 0
    s3, rep3 = d.draw_era_sample(rows, 100, "seed")
    assert len(s3) == 60 and rep3["cells"]["O|P0"]["shortfall"] == 70


def test_series_rules_hash_file_roundtrip(tmp_path):
    p = tmp_path / "rules.json"
    d.write_series_rules(p)
    d.require_series_rules(p, require_committed=False)
    with pytest.raises(d.Refused):
        d.require_series_rules(tmp_path / "nope.json", require_committed=False)
    p.write_text(json.dumps({**d.series_rules_doc(), "funcs_sha256": "0"}))
    with pytest.raises(d.Refused):
        d.require_series_rules(p, require_committed=False)
    with pytest.raises(d.Refused):
        d.write_series_rules(p)  # never rewritten


# ---- era fetch ----------------------------------------------------------------------------------------------


def era_net(trades_after=()):
    ms = []
    for i in range(4):
        ms.append(gmarket(100 + i, f"2026-03-04T1{i}:07:00Z", fee="sports", event_id=f"ES{i}"))
    for i in range(5):
        ms.append(gmarket(200 + i, f"2026-03-04T0{i}:22:00Z", fee="crypto", event_id=f"EC{i}"))
    ms.append(gmarket(300, "2026-03-04T05:07:00Z", fee="weather"))
    ms.append(gmarket(301, "2026-03-04T06:07:00Z", title="Highest temperature in Paris on March 4?"))
    ms.append(gmarket(302, "2026-03-04T07:07:00Z", fee="crypto"))  # in an excluded history run
    ms.append(gmarket(303, "2026-03-04T08:07:00Z", fee="crypto", created="2026-03-02T00:00:00Z"))  # life < 4 d
    ms.append(gmarket(304, "2026-03-04T09:07:00Z", fee="crypto", closed=False, prices=None))  # still open: kept (censored)
    return FakeNet(markets=ms, trades_after=trades_after)


def _amend(tmp_path, kind, cats=("sports",), decision="as_declared"):
    rdir = tmp_path / "hist" / ("h7_cb4_era" if kind == "era" else "h7_cb4_series")
    f = tmp_path / "amend.json"
    doc = json.loads(f.read_text()) if f.exists() else {"decision": decision, "sports_fee_categories": list(cats)}
    doc[f"{kind}_frame_report_sha256"] = h5_seal.sha256_file(rdir / "frame_report.json")
    f.write_text(json.dumps(doc))
    return f


def era_kw(tmp_path, net, **kw):
    hist = tmp_path / "hist"
    (hist / "h2_main").mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"market_id": ["302"]}).to_csv(hist / "h2_main" / "sample.csv.gz", index=False)
    base = dict(seed="s", per_cell=3, periods=[("P0", ep("2026-03-01"), ep("2026-03-05"))], exclude_runs=["h2_main"],
                h5_seal_copies=[_h5_copy(tmp_path, ("100",))], key=KEY, now=NOW, wall_clock=_wall(), sleep=lambda s: None,
                live_check=None, windows_per_day=96, window_minutes=15, disk_cap=10**8, require_committed=False)
    stage = kw.pop("stage", "all")
    rdir = hist / "h7_cb4_era"
    if stage == "all" and kw.pop("auto_frame", True) and not (rdir / "frame_report.json").exists():
        d.era_fetch(hist, "h7_cb4_era", net, **{**base, "stage": "frame"})
    if stage == "all" and (rdir / "frame_report.json").exists():
        base["amendment_file"] = _amend(tmp_path, "era")
    base.update(kw)
    return d.era_fetch(hist, "h7_cb4_era", net, stage=stage, **base)


def test_era_fetch_complete_guard_and_cap(tmp_path):
    net = era_net(trades_after=[NOW + 10, NOW + 99])
    m = era_kw(tmp_path, net)
    assert m["status"] == "era_fetch_complete" and m["complete"] is True and m["stopped"] is None
    rdir = tmp_path / "hist" / "h7_cb4_era"
    fr = json.loads((rdir / "frame_report.json").read_text())
    rules = fr["rules"]
    assert rules["weather"] == 2 and rules["history_sample_overlap"] == 1 and rules["h5_overlap"] == 1 and rules["life_lt_min"] == 1
    sample = pd.read_csv(rdir / "sample.csv.gz", dtype=str, keep_default_na=False)
    # cell S has 3 eligible (4 sports - the h5 id), cell O has 5 crypto + the censored open one = 6 -> 3 sampled
    assert sorted(set(sample.group)) == ["O", "S"] and (sample.group == "O").sum() == 3 and (sample.group == "S").sum() == 3
    # outcome columns live only in the guarded file
    for f in ("sample.csv.gz", "frame.csv.gz"):
        cols = set(pd.read_csv(rdir / f, nrows=0).columns)
        assert not cols & set(d.OUTCOME_FIELDS), f
    og = pd.read_csv(rdir / "outcomes_guarded.csv.gz", dtype=str, keep_default_na=False)
    assert {"closed", "outcome_prices", "closed_time", "volume"} <= set(og.columns) and "304" in set(og.market_id)
    # rows at/after the cap are dropped and counted
    man = json.loads((rdir / "manifest.json").read_text())
    assert man["counts"]["items_done"] == 6 and man["counts"]["trade_rows_dropped_post_cap"] == 12
    tr = pd.read_csv(rdir / "trades" / f"{sample.market_id.iloc[0]}.csv.gz")
    assert (tr.ts < NOW).all() and len(tr) == 3
    assert man["request_clock_now"] == iso(NOW) and man["params"]["cap_utc"] == iso(NOW)
    assert not (rdir / "frame_partial.jsonl").exists() and not (rdir / "frame_partial_guarded.jsonl").exists()
    # prices were requested for the YES token only, once per sampled market
    assert all(t.endswith("a") for t in net.price_calls) and len(net.price_calls) == 6


def test_era_fetch_resumes_without_refetching(tmp_path):
    net = era_net()
    n = {"c": 0}

    def stop():
        n["c"] += 1
        return n["c"] > 4  # walk checks once per day (4) -> then stop before the first market

    m1 = era_kw(tmp_path, net, should_stop=stop)
    assert m1["complete"] is False and m1["stopped"] == "should_stop"
    m2 = era_kw(tmp_path, net)
    assert m2["status"] == "era_fetch_complete"
    first_prices = len(net.price_calls)
    assert first_prices == 6
    m3 = era_kw(tmp_path, net)  # idempotent once complete
    assert m3["status"] == "era_fetch_complete" and len(net.price_calls) == first_prices


def test_era_fetch_budget_chunks_resume(tmp_path):
    net = era_net()
    m1 = era_kw(tmp_path, net, budget_min=1e-9)
    assert m1["complete"] is False and "budget" in m1["stopped"]
    for _ in range(3):
        m = era_kw(tmp_path, net, budget_min=None)
        if m.get("complete"):
            break
    assert m["status"] == "era_fetch_complete"
    assert len(set(net.price_calls)) == len(net.price_calls) == 6  # never refetched


def test_era_t_seal_refuses_new_chunk_and_marks_not_run(tmp_path):
    net = era_net()
    late = _wall(d.T_SEAL_EPOCH + 5)
    era_kw(tmp_path, net, stage="frame")
    n_before = net.requests
    m = era_kw(tmp_path, net, wall_clock=late, auto_frame=False)
    assert m["status"] == "not_run_deadline" and net.requests == n_before
    rdir = tmp_path / "hist" / "h7_cb4_era"
    assert (rdir / d.NOT_RUN_FILE).exists() and json.loads((rdir / "manifest.json").read_text())["stopped"] == "not_run_deadline"
    # a later call (even before the clock moves back) never refetches or rewrites the cap
    m2 = era_kw(tmp_path, net)
    assert m2["status"] == "not_run_deadline" and net.requests == n_before


def test_era_t_seal_after_complete_is_still_complete(tmp_path):
    net = era_net()
    assert era_kw(tmp_path, net)["status"] == "era_fetch_complete"
    assert era_kw(tmp_path, net, wall_clock=_wall(d.T_SEAL_EPOCH + 5))["status"] == "era_fetch_complete"


def test_era_collector_health_pause_and_429_limit(tmp_path):
    net = era_net()
    m = era_kw(tmp_path, net, health_check=lambda t: (False, "stale"), auto_frame=False)
    assert m["stopped"].startswith("paused_collector_health") and m["transient"] is True and net.requests == 0


def test_era_disk_budget_stops_cleanly(tmp_path):
    net = era_net()
    m = era_kw(tmp_path, net, disk_cap=3000)
    assert "disk_budget" in str(m.get("stopped"))


def test_fetch_refuses_sealed_and_foreign_run_ids(tmp_path):
    net = era_net()
    era_kw(tmp_path, net)
    rdir = tmp_path / "hist" / "h7_cb4_era"
    h5_seal.seal_run(rdir, declaration_base=h5_seal.DECLARATION_H7_ERA, trials_path=tmp_path / "t.jsonl")
    with pytest.raises(d.Refused):
        era_kw(tmp_path, net)
    for rid in ("h6_weather", "h5_cb1", "h3_power", "h4_seal", "h5_cb1_ladders", "h7_cb4_series"):
        with pytest.raises(d.Refused):
            d.era_fetch(tmp_path / "x", rid, net)


# ---- command layer ------------------------------------------------------------------------------------------


def test_cmd_fetch_refusals(tmp_path, capsys):
    net = era_net()
    seal = _h5_copy(tmp_path)
    ok = dict(transport=net, root=str(tmp_path / "hist"), exclude_seal_ids=str(seal), data_dumps=str(tmp_path / "dd"),
              wall_clock=_wall(), now=NOW)
    (tmp_path / "dd").mkdir()

    def run(**kw):
        capsys.readouterr()
        rc = d.cmd_fetch(_ns(**{**ok, **kw}), require_committed=False, allow_nondeclared=True)
        return rc, capsys.readouterr().out

    rc, out = run(exclude_seal_ids="")
    assert rc == 2 and "h5_cb1_SEAL.json" in out
    rc, out = run(exclude_seal_ids=str(tmp_path / "seals" / "nope" / "h5_cb1_SEAL.json"))
    assert rc == 2 and "missing" in out
    rc, out = run(run_id="h6_weather")
    assert rc == 2 and "refuses" in out
    rc, out = run(root=str(tmp_path / "cb1_extract" / "x"))
    assert rc == 2 and "extract root" in out
    rc, out = run(data_dumps_cap_gb=-1.0)
    assert rc == 2 and "refusing to start" in out
    rc, out = run(kind="series")  # series rule file absent
    assert rc == 2 and "series-rule" in out
    # declared arguments are enforced unless the test escape hatch is on
    capsys.readouterr()
    rc = d.cmd_fetch(_ns(**{**ok, "per_cell": 5}), require_committed=False)
    assert rc == 2 and "per_cell" in capsys.readouterr().out
    rc = d.cmd_fetch(_ns(**{**ok, "seed": "other"}), require_committed=False)
    assert rc == 2 and "seed" in capsys.readouterr().out


def test_cmd_fetch_requires_committed_seal_copy(tmp_path, capsys):
    seal = _h5_copy(tmp_path)  # exists but is not tracked/committed by git
    rc = d.cmd_fetch(_ns(transport=era_net(), root=str(tmp_path / "hist"), exclude_seal_ids=str(seal)), allow_nondeclared=True)
    assert rc == 2 and "not committed" in capsys.readouterr().out


def test_cmd_fetch_not_run_at_t_seal_exit_0_and_flag(tmp_path, capsys):
    seal = _h5_copy(tmp_path)
    (tmp_path / "dd").mkdir()
    rc = d.cmd_fetch(_ns(transport=era_net(), root=str(tmp_path / "hist"), exclude_seal_ids=str(seal), data_dumps=str(tmp_path / "dd"),
                         wall_clock=_wall(d.T_SEAL_EPOCH + 1)), require_committed=False, allow_nondeclared=True)
    out = capsys.readouterr().out
    assert rc == 0 and '"status": "not_run_deadline"' in out and '"status": "era_fetch_complete"' not in out


# ---- series fetch ---------------------------------------------------------------------------------------------


def gevent(eid, end, *, series="S1", slug="btc-daily", winner="Up", created=None, title="BTC up or down", fee="crypto",
           mid=None, closed=True, outcomes='["Up","Down"]', closed_time=None, n=1):
    mid = mid or f"M{eid}"
    prices = '["1","0"]' if winner == "Up" else '["0","1"]'
    ct = closed_time if closed_time is not None else iso(d._parse_ts(end) + 3600)
    if n == 1:
        ms = [gmarket(mid, end, fee=fee, created=created or iso(d._parse_ts(end) - 2 * 86400), closed=closed, prices=prices,
                      outcomes=outcomes, closed_time=ct, title=title)]
    else:
        ms = []
    return {"id": eid, "title": title, "endDate": end, "createdAt": created or iso(d._parse_ts(end) - 2 * 86400),
            "closed": closed, "series": [{"id": series, "slug": slug}] if series else [], "markets": ms}


def series_net(days=12, **kw):
    evs = []
    for k in range(days):
        end = iso(ep("2026-03-01T12:00:00Z") + k * 86400)
        evs.append(gevent(f"ev{k}", end, winner="Up" if k % 3 else "Down"))
    evs += [gevent(f"wx{k}", iso(ep("2026-03-01T12:00:00Z") + k * 86400), series="W1", slug="wx", title="Highest temperature in NYC on March 4?")
            for k in range(6)]
    evs += [gevent("lone", "2026-03-05T12:00:00Z", series="L1", slug="lone"), gevent("noseries", "2026-03-05T13:00:00Z", series=None)]
    return FakeNet(events=evs, **kw)


def series_kw(tmp_path, net, **kw):
    hist = tmp_path / "hist"
    (hist / "h2_main").mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"market_id": ["Mev5"]}).to_csv(hist / "h2_main" / "sample.csv.gz", index=False)
    base = dict(seed="s", n_series=5, n_sports=2, members=31, roll_from="2026-03-01", walk_from="2026-03-01",
                exclude_runs=["h2_main"], h5_seal_copies=[_h5_copy(tmp_path, ("Mev9",))], key=KEY, now=NOW, wall_clock=_wall(),
                sleep=lambda s: None, live_check=None, disk_cap=10**8, walk_base_days=7, min_width_s=3600, require_committed=False)
    stage = kw.pop("stage", "all")
    rdir = hist / "h7_cb4_series"
    if stage == "all" and kw.pop("auto_frame", True) and not (rdir / "frame_report.json").exists():
        d.series_fetch(hist, "h7_cb4_series", net, **{**base, "stage": "frame"})
    if stage == "all" and (rdir / "frame_report.json").exists():
        base["amendment_file"] = _amend(tmp_path, "series")
    base.update(kw)
    return d.series_fetch(hist, "h7_cb4_series", net, stage=stage, **base)


def test_series_fetch_units_exclusions_and_files(tmp_path):
    net = series_net(series_ok=True)
    m = series_kw(tmp_path, net)
    assert m["status"] == "series_fetch_complete" and m["complete"] is True
    rdir = tmp_path / "hist" / "h7_cb4_series"
    fr = json.loads((rdir / "frame_report.json").read_text())
    ur = json.loads((rdir / "units_report.json").read_text())
    assert fr["walk"]["events_no_series"] == 1 and fr["series_ge_2_members"] == 2 and "daily|crypto" in fr["series_by_cadence_category"]
    fr = ur
    assert fr["series_weather_excluded"] == 1 and fr["series_lt_2_members"] == 1  # the 1-member series
    assert fr["series_sampled_non_sports"] == 1
    # r_to = min(NOW - 3d, T_seal) - 2d = 03-15: preds ev0..ev11 are all <= 03-12, 11 candidates (last has no successor)
    assert fr["units_candidate"] == 11
    # excluded events: history overlap Mev5 drops units (ev4->ev5) and (ev5->ev6); h5 overlap Mev9 drops (ev8->ev9) and (ev9->ev10)
    drops = fr["unit_drops"]
    assert drops["excluded_event_history_sample_overlap"] == 2 and drops["excluded_event_h5_overlap"] == 2
    units = d._load_jsonl_gz(rdir / "units.jsonl.gz")
    assert len(units) == 11 - 4 - 1 + 0 or len(units) >= 5  # ev11 has no successor (11 candidates are ev0..ev10)
    u = units[0]
    assert u["cadence"] == "daily" and u["V_end_h"] == 12.0 and "side_token_index" not in u and "pred_winner_key" not in u
    # t0 is the predecessor's closedTime (end + 1h); a side is only in the guarded file
    assert u["t0_epoch"] == u["pred_end_epoch"] + 3600
    og = pd.read_csv(rdir / "outcomes_guarded.csv.gz", dtype=str, keep_default_na=False)
    assert len(og) == len(units) and set(og.pred_winner_key) <= {"up", "down"}
    # probe: outcome-like keys are dropped by guard and never written
    probe = json.loads((rdir / "probe.json").read_text())
    assert probe["usable"] is True and "outcomePrices" not in probe["item_keys_without_outcome_fields"]
    # the rolled-into token: the 'Down' predecessor winner (k % 3 == 0) rolls into token index 1 (price history asks the b-token)
    by = {r["unit_id"]: r for r in og.to_dict("records")}
    idx = {uu["unit_id"]: int(by[uu["unit_id"]]["side_token_index"]) for uu in units}
    assert set(idx.values()) == {0, 1}
    assert any(t.endswith("b") for t in net.price_calls) and any(t.endswith("a") for t in net.price_calls)
    # fetch windows: [t0' - 3h, V_end + 2h] with t0' = t0 - 12h - 6h
    prog = [json.loads(line) for line in (rdir / "progress.jsonl").read_text().splitlines()]
    p0 = next(p for p in prog if p["unit_id"] == u["unit_id"])
    assert p0["window"][0] == int(u["t0_epoch"] - 21 * 3600) and p0["window"][1] == int(u["t0_epoch"] + 14 * 3600)
    assert not (rdir / "walk_partial.jsonl").exists()


def test_series_fetch_resumes_walk_and_fetch(tmp_path):
    net = series_net()
    n = {"c": 0}

    def stop():
        n["c"] += 1
        return n["c"] == 2  # one base window recorded, then pause

    m1 = series_kw(tmp_path, net, should_stop=stop, walk_base_days=3, stage="frame")
    assert m1["complete"] is False and m1["stopped"] == "should_stop"
    assert (tmp_path / "hist" / "h7_cb4_series" / "walk_partial.jsonl").exists()
    m2 = series_kw(tmp_path, net, walk_base_days=3)
    assert m2["status"] == "series_fetch_complete"
    assert len(net.price_calls) == 2 * m2["counts"]["items_done"]  # successor + winning predecessor per unit, once each
    n_req = net.requests
    assert series_kw(tmp_path, net, walk_base_days=3)["status"] == "series_fetch_complete" and net.requests == n_req


def test_series_walk_halves_capped_window_and_drops_at_min_width(tmp_path, monkeypatch):
    monkeypatch.setattr(hb_mod(), "GAMMA_OFFSET_CAP", 200)
    evs = [gevent(f"c{k}", f"2026-03-02T{10 + k // 60:02d}:{k % 60:02d}:00Z", series="S1") for k in range(230)]
    net = FakeNet(events=evs)
    lim = hb_mod().Limiter(net, rps=4.0, sleep=lambda s: None)
    (tmp_path / "w").mkdir()
    ev, g, rep, stopped = d.walk_series_events(lim, ep("2026-03-02"), ep("2026-03-03"), (True,), rdir=tmp_path / "w", base_days=7, min_width_s=3600)
    assert stopped is None and rep["splits"] >= 1 and len(ev) == 230 and rep["windows_dropped_capped"] == 0
    # events that all end in one 1h slot and still cap -> the slot is dropped and counted
    evs2 = [gevent(f"d{k}", f"2026-03-02T10:{k // 60:02d}:{k % 60:02d}Z", series="S1") for k in range(230)]
    lim2 = hb_mod().Limiter(FakeNet(events=evs2), rps=4.0, sleep=lambda s: None)
    (tmp_path / "w2").mkdir()
    ev2, _g2, rep2, _s = d.walk_series_events(lim2, ep("2026-03-02"), ep("2026-03-03"), (True,), rdir=tmp_path / "w2", min_width_s=3600)
    assert rep2["windows_dropped_capped"] == 1 and rep2["rows_in_dropped_windows"] == 200 and len(ev2) == 0


def hb_mod():
    from astrolabe.research_lab import history_backfill as hb

    return hb


def test_series_t_seal_deadline_and_dependent_seal(tmp_path):
    net = series_net()
    m = series_kw(tmp_path, net, should_stop=lambda: True)  # incomplete
    assert m["complete"] is False
    late = series_kw(tmp_path, net, wall_clock=_wall(d.T_SEAL_EPOCH + 5))
    assert late["status"] == "not_run_deadline"
    root = tmp_path / "hist"
    seals = tmp_path / "seals2"
    out = d.seal_h7_run(root, "h7_cb4_series", seals_dir=seals, trials_path=tmp_path / "t.jsonl", wall_clock=_wall(d.T_SEAL_EPOCH + 5))
    assert out["not_run"] is True and (seals / "h7_cb4_series_NOT_RUN.json").exists()
    assert not (root / "h7_cb4_series" / "SEAL.json").exists() and not (seals / "h7_cb4_series_SEAL.json").exists()
    assert not (tmp_path / "t.jsonl").exists()


# ---- seals ----------------------------------------------------------------------------------------------------------


def _both_runs(tmp_path):
    era_kw(tmp_path, era_net())
    series_kw(tmp_path, series_net())
    return tmp_path / "hist"


def test_seal_both_split_listing_and_verify(tmp_path):
    root = _both_runs(tmp_path)
    seals = tmp_path / "seals_out"
    trials = tmp_path / "trials.jsonl"
    opened: list[str] = []
    real_gz = gzip.open

    def spy(f, *a, **k):
        opened.append(str(f))
        return real_gz(f, *a, **k)

    import pytest as _p  # noqa: PLC0415

    mp = _p.MonkeyPatch()
    mp.setattr(gzip, "open", spy)
    real_csv = pd.read_csv

    def spy_csv(f, *a, **k):
        opened.append(str(f))
        return real_csv(f, *a, **k)

    mp.setattr(pd, "read_csv", spy_csv)
    rc = d.cmd_seal(types.SimpleNamespace(run_ids="h7_cb4_series,h7_cb4_era", root=str(root), seals_dir=str(seals), trials_path=str(trials)))
    mp.undo()
    assert rc == 0
    # the split never opened a price, trade or outcome file
    assert opened and not any(("outcomes_guarded" in p or "/prices/" in p or "/trades/" in p) for p in opened)
    era = json.loads((root / "h7_cb4_era" / "SEAL.json").read_text())
    ser = json.loads((root / "h7_cb4_series" / "SEAL.json").read_text())
    assert era["listing_sha256"] == json.loads((seals / "h7_cb4_era_SEAL.json").read_text())["listing_sha256"]
    sp = ser["split"]
    assert sp["d_split4"] and sp["n_screen"] + sp["n_holdout"] + sp["n_embargo"] == sp["n_universe"]
    assert sp["n_holdout"] <= 0.40 * sp["n_universe"] and "no price, trade or outcome file" in sp["inputs"]
    assert sp["era_listing"] == "present" and sp["era_listing_sha256"] == era["listing_sha256"]
    assert ser["declaration"]["dataset_role"].startswith("CB4-S series roll flow")
    assert (seals / "h7_cb4_series_SEAL.json").read_bytes() == (root / "h7_cb4_series" / "SEAL.json").read_bytes()
    lines = [json.loads(line) for line in trials.read_text().splitlines()]
    assert len(lines) == 2 and {x["run_id"] for x in lines} == {"h7_cb4_era", "h7_cb4_series"}
    assert all(x["kind"] == "history_seal_declaration" and x["source"] == "creative_batch_4:cb4_f_seal" and x["n_tests"] == 0 for x in lines)
    assert d.cmd_verify_seal(types.SimpleNamespace(run_ids="h7_cb4_era,h7_cb4_series", root=str(root), seals_dir=str(seals))) == 0
    # sealing again is idempotent (reported, nothing rewritten); a modified file breaks verification
    assert d.cmd_seal(types.SimpleNamespace(run_ids="h7_cb4_era,h7_cb4_series", root=str(root), seals_dir=str(seals), trials_path=str(trials))) == 0
    assert len(trials.read_text().splitlines()) == 2
    (root / "h7_cb4_series" / "ACCESS_LOG.jsonl").write_text("x\n")  # outside the listing
    assert d.cmd_verify_seal(types.SimpleNamespace(run_ids="h7_cb4_series", root=str(root), seals_dir=str(seals))) == 0
    (root / "h7_cb4_series" / "extra.txt").write_text("x")
    assert d.cmd_verify_seal(types.SimpleNamespace(run_ids="h7_cb4_series", root=str(root), seals_dir=str(seals))) == 1


def test_seal_drops_units_with_era_member_by_id(tmp_path):
    root = tmp_path / "hist"
    series_kw(tmp_path, series_net(), exclude_runs=[])
    era_dir = root / "h7_cb4_era"
    era_dir.mkdir()
    pd.DataFrame({"market_id": ["Mev3"]}).to_csv(era_dir / "sample.csv.gz", index=False)  # a market of ev3
    (era_dir / "manifest.json").write_text(json.dumps({"run_id": "h7_cb4_era", "complete": True, "stopped": None, "request_clock_now": "t"}))
    units = d._load_jsonl_gz(root / "h7_cb4_series" / "units.jsonl.gz")
    out = d.seal_h7_run(root, "h7_cb4_series", seals_dir=tmp_path / "s", trials_path=tmp_path / "t.jsonl")
    # ev3 is pred of one unit and succ of another
    assert out["n_dropped_era_overlap"] == 2 and out["n_universe"] == len(units) - 2


def test_seal_refuses_unfinished_foreign_and_sealed_data(tmp_path):
    root = tmp_path / "hist"
    era_kw(tmp_path, era_net(), should_stop=lambda: True)  # unfinished, before T_seal
    with pytest.raises(h5_seal.SealError):
        d.seal_h7_run(root, "h7_cb4_era", seals_dir=tmp_path / "s", trials_path=tmp_path / "t.jsonl", wall_clock=_wall())
    for rid in ("h5_cb1", "h6_weather", "h3_power", "h2_main"):
        with pytest.raises((h5_seal.SealError, d.Refused)):
            d.seal_h7_run(root, rid, seals_dir=tmp_path / "s")
    assert d.cmd_seal(types.SimpleNamespace(run_ids="h5_cb1", root=str(root), seals_dir=None)) == 1


def test_seal_one_not_run_other_sealed_exit_0(tmp_path):
    root = tmp_path / "hist"
    series_kw(tmp_path, series_net())
    era_kw(tmp_path, era_net(), should_stop=lambda: True)  # era incomplete
    seals = tmp_path / "s"
    rc = d.cmd_seal(types.SimpleNamespace(run_ids="h7_cb4_era,h7_cb4_series", root=str(root), seals_dir=str(seals),
                                          trials_path=str(tmp_path / "t.jsonl"), wall_clock=_wall(d.T_SEAL_EPOCH + 1)))
    assert rc == 0
    assert (seals / "h7_cb4_era_NOT_RUN.json").exists() and (seals / "h7_cb4_series_SEAL.json").exists()
    assert not (seals / "h7_cb4_era_SEAL.json").exists()
    ser = json.loads((root / "h7_cb4_series" / "SEAL.json").read_text())
    assert ser["split"]["era_listing"] == "absent"
    assert d.cmd_verify_seal(types.SimpleNamespace(run_ids="h7_cb4_era,h7_cb4_series", root=str(root), seals_dir=str(seals))) == 0


def test_h5_seal_allowlist_extended_not_broken():
    assert h5_seal.check_run_id("h7_cb4_era") == "h7_cb4_era" and h5_seal.check_run_id("h6_weather") == "h6_weather"
    with pytest.raises(h5_seal.SealError):
        h5_seal.check_run_id("h7_cb4_era", h5_seal.H5_RUN_IDS)
    with pytest.raises(h5_seal.SealError):
        h5_seal.check_run_id("h2_main")


def test_script_fetch_seal_and_rules_subcommands(tmp_path, capsys, monkeypatch):
    assert script.main(["series-rules", "--path", str(tmp_path / "r.json")]) == 0
    assert json.loads((tmp_path / "r.json").read_text()) == d.series_rules_doc()
    # real argparse path: refuses without the h5 seal copy; alias subcommands parse
    assert script.main(["era-fetch", "--root", str(tmp_path / "h")]) == 2
    assert script.main(["series-fetch", "--root", str(tmp_path / "h")]) == 2
    assert script.main(["fetch", "--kind", "era", "--run-id", "h6_weather", "--root", str(tmp_path / "h")]) == 2
    out = capsys.readouterr().out
    assert "h5_cb1_SEAL.json" in out and "refuses" in out
    assert script.main(["seal", "--run-ids", "h5_cb1", "--root", str(tmp_path / "h")]) == 1
    # the analysis module now exists (and a real pilot would use the network); simulate it being absent -> exit 2
    _hide_analysis(monkeypatch)
    assert script.main(["pilot"]) == 2


def test_datetime_utc_helpers():
    assert d._iso(0) == "1970-01-01T00:00:00Z" and d._parse_ts("2026-03-01 10:00:00+00") == ep("2026-03-01T10:00:00Z")
    assert datetime.fromtimestamp(d._parse_ts("2026-03-01T10:00:00.123Z"), UTC).hour == 10


# ---- queue specs ----------------------------------------------------------------------------------------------


def test_queue_specs_valid_and_repeat_regexes_match_only_true_completion():
    import re  # noqa: PLC0415

    jobs = Path(__file__).resolve().parents[3] / "docs" / "research_lab" / "queue" / "jobs"
    specs = {p.stem: json.loads(p.read_text()) for p in sorted(jobs.glob("q008[0-3]_*.json"))}
    assert len(specs) == 4 and all(s["id"] == k for k, s in specs.items())
    scripts_dir = Path(__file__).resolve().parents[2] / "scripts"
    for s in specs.values():
        assert (scripts_dir.parent / s["argv"][0]).exists() and s["family"] and isinstance(s["priority"], int)
    q80, q81, q82, q83 = (specs[k] for k in sorted(specs))
    assert q80["priority"] == 62 and "--release-stream" in q80["argv"] and q80["argv"][q80["argv"].index("--data-dumps-max-gb") + 1] == "12"
    for q in (q81, q82):
        assert q["priority"] in (58, 61) and q["resources"]["lane"] == "net" and "q0018_h5_cb1_seal" in q["depends_on"]
        assert "../docs/research_lab/seals/h5_cb1_SEAL.json" in q["argv"] and q["argv"][q["argv"].index("--cap-at") + 1] == "2026-10-22T00:00Z"
    assert q83["depends_on"] == ["q0083b_h7_deadline_recorder"] and "repeat" not in q83
    f81 = json.loads((jobs / "q0081f_h7_cb4_era_frame.json").read_text())
    f82 = json.loads((jobs / "q0082f_h7_cb4_series_frame.json").read_text())
    rec = json.loads((jobs.parent / "drafts" / "q0083b_h7_deadline_recorder.json").read_text())  # one-shot draft, created at T_seal
    assert f81["argv"][1] == "era-frame" and f82["argv"][1] == "series-frame" and rec["depends_on"] == [] and rec["argv"][1] == "record-deadline"
    assert "q0081f_h7_cb4_era_frame" in q81["depends_on"] and "q0082f_h7_cb4_series_frame" in q82["depends_on"]
    assert "q0081a_h7_release_gate" in q81["depends_on"] and "q0081a_h7_release_gate" in q82["depends_on"]  # coordinator gate kept
    assert "q0080a_cb4_freezecheck_gate" in q80["depends_on"]
    assert (scripts_dir.parent / rec["argv"][0]).exists() and "--group-s-amendment" in q81["argv"] and "--group-s-amendment" in q82["argv"]
    assert "repeat" not in rec and not (jobs / "q0083b_h7_deadline_recorder.json").exists()  # a polling repeat starves the cpu lane
    rxf = re.compile(f81["repeat"]["until_log_regex"])
    assert rxf.search(json.dumps({"status": "era_frame_complete"})) and not rxf.search(json.dumps({"status": None, "stopped": "frame_paused"}))
    # the repeat regexes match the real terminal output lines and nothing else
    rx80 = re.compile(q80["repeat"]["until_log_regex"])
    assert rx80.search(json.dumps({"backfill_complete": True, "written": 3}, sort_keys=True))
    for bad in ({"backfill_complete": False}, {"stopped": "refused_data_dumps_over_cap"}, {"error": "backfill_complete"}):
        assert not rx80.search(json.dumps(bad, sort_keys=True))
    rx81, rx82 = re.compile(q81["repeat"]["until_log_regex"]), re.compile(q82["repeat"]["until_log_regex"])
    assert rx81.search(json.dumps({"status": "era_fetch_complete"})) and rx81.search(json.dumps({"status": "not_run_deadline"}))
    assert rx82.search(json.dumps({"status": "series_fetch_complete"})) and not rx82.search(json.dumps({"status": "era_fetch_complete"}))
    for bad in ({"status": None, "stopped": "budget reached"}, {"stopped": "paused_collector_health: x"}, {"refused": "era_fetch_complete"}):
        assert not rx81.search(json.dumps(bad)) and not rx82.search(json.dumps(bad))


def test_cmd_fetch_end_to_end_wiring_era_and_series(tmp_path, capsys):
    seal = _h5_copy(tmp_path)
    (tmp_path / "dd").mkdir()
    hist = tmp_path / "hist"
    for rid in ("h1_first", "h2_main", "h3_power"):
        (hist / rid).mkdir(parents=True)
        pd.DataFrame({"market_id": ["1"]}).to_csv(hist / rid / "sample.csv.gz", index=False)
    rules = tmp_path / "rules.json"
    d.write_series_rules(rules)
    base = dict(root=str(hist), exclude_seal_ids=str(seal), data_dumps=str(tmp_path / "dd"), wall_clock=_wall(), now=NOW,
                exclude_runs="h1_first,h2_main,h3_power", series_rules_file=str(rules))
    ev = [gevent(f"ev{k}", iso(ep("2026-03-01T12:00:00Z") + k * 86400)) for k in range(6)]
    net = FakeNet(markets=[gmarket(1, "2026-03-04T10:07:00Z")], events=ev)
    capsys.readouterr()
    am = tmp_path / "amend.json"
    kwe = dict(kind="era", transport=net, periods="2026-03-01/2026-03-05", group_s_amendment=str(am), **base)
    # the amendment does not exist yet: the frame stage runs and stops, the full run refuses
    rc = d.cmd_fetch(_ns(stage="frame", **kwe), require_committed=False, allow_nondeclared=True)
    out = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert rc == 0 and out["status"] == "era_frame_complete"
    rc = d.cmd_fetch(_ns(stage="all", **kwe), require_committed=False, allow_nondeclared=True)
    assert rc == 2 and "amendment" in capsys.readouterr().out
    am.write_text(json.dumps({"decision": "as_declared", "sports_fee_categories": ["sports"],
                              "era_frame_report_sha256": h5_seal.sha256_file(hist / "h7_cb4_era" / "frame_report.json"),
                              "series_frame_report_sha256": "x"}))
    rc = d.cmd_fetch(_ns(stage="all", **kwe), require_committed=False, allow_nondeclared=True)
    out = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert rc == 0 and out["status"] == "era_fetch_complete" and out["stopped"] is None
    kws = dict(kind="series", transport=net, roll_from="2026-03-01", n_series=3, group_s_amendment=str(am), **base)
    assert d.cmd_fetch(_ns(stage="frame", **kws), require_committed=False, allow_nondeclared=True) == 0
    assert json.loads(capsys.readouterr().out.strip().splitlines()[-1])["status"] == "series_frame_complete"
    doc = json.loads(am.read_text())
    doc["series_frame_report_sha256"] = h5_seal.sha256_file(hist / "h7_cb4_series" / "frame_report.json")
    am.write_text(json.dumps(doc))
    rc = d.cmd_fetch(_ns(stage="all", **kws), require_committed=False, allow_nondeclared=True)
    out = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert rc == 0 and out["stopped"] is None


def test_release_transient_failure_is_retried_then_succeeds(tmp_path):
    snap = tmp_path / "snapshots"
    make_capture(snap, "r0", S0, [], with_files=False)
    blobs, entries = {}, []
    for name, rows, cols in (("rows.csv.gz", _rows_a(), ROW_COLS), ("rows_ext.csv.gz", _ext_a(), EXT_COLS)):
        p = tmp_path / name
        _gz(p, pd.DataFrame(rows, columns=cols))
        ap = f"data-dumps/research_lab/snapshots/r0/{name}"
        blobs[ap] = p.read_bytes()
        entries.append({"path": ap, "bytes": 1000, "sha256": _sha(blobs[ap])})
    calls = {"n": 0}

    def restore(tag, globs, dest):
        calls["n"] += 1
        if calls["n"] < 3:
            return False  # two transient failures
        for g in globs:
            (Path(dest) / g).parent.mkdir(parents=True, exist_ok=True)
            (Path(dest) / g).write_bytes(blobs[g])
        return True

    rel = d.ReleaseCopies(tmp_path / "scr", catalogue=_catalogue(tmp_path, entries), restore=restore, retries=3, backoff_s=0, sleep=lambda s: None)
    r = d.run_closewin(snap, tmp_path / "none", tmp_path / "root", mode="backfill", since=S0, release=rel)
    assert r["written"] == 1 and r["missing"] == 0 and calls["n"] == 3


def test_release_only_captures_absent_from_host_are_listed_and_extracted_or_recorded(tmp_path):
    snap = tmp_path / "snapshots"
    make_capture(snap, "20261012T000000Z_aaaa0001", S0, _rows_a(), _ext_a())  # on the host
    cid = "20261012T020000Z_bbbb0002"  # only in a release; no host manifest
    blobs, entries = {}, []
    for name, payload in (("rows.csv.gz", (_rows_a(), ROW_COLS)), ("rows_ext.csv.gz", (_ext_a(), EXT_COLS))):
        p = tmp_path / name
        _gz(p, pd.DataFrame(payload[0], columns=payload[1]))
        ap = f"data-dumps/research_lab/snapshots/{cid}/{name}"
        blobs[ap] = p.read_bytes()
        entries.append({"path": ap, "bytes": 1000, "sha256": _sha(blobs[ap])})
    mp = f"data-dumps/research_lab/snapshots/{cid}/manifest.json"
    blobs[mp] = json.dumps({"state": "complete", "started_utc": S1}).encode()
    entries.append({"path": mp, "bytes": 100, "sha256": _sha(blobs[mp])})
    cat = _catalogue(tmp_path, entries)
    assert cat.snapshot_dirs() == {cid: "2026-10-12T02:00:00Z"}
    # without --release-stream: recorded as no_host_manifest (counted, never silently absent)
    r = d.run_closewin(snap, tmp_path / "none", tmp_path / "r1", mode="backfill", since=S0, catalogue=cat)
    man = json.loads((tmp_path / "r1" / "manifest.json").read_text())
    assert man["captures"][cid]["reason"] == "no_host_manifest" and r["n_release_only"] == 1 and r["backfill_complete"] is True

    def restore(tag, globs, dest):
        for g in globs:
            (Path(dest) / g).parent.mkdir(parents=True, exist_ok=True)
            (Path(dest) / g).write_bytes(blobs[g])
        return True

    rel = d.ReleaseCopies(tmp_path / "scr", catalogue=cat, restore=restore)
    r = d.run_closewin(snap, tmp_path / "none", tmp_path / "r2", mode="backfill", since=S0, catalogue=cat, release=rel)
    man = json.loads((tmp_path / "r2" / "manifest.json").read_text())
    assert man["captures"][cid]["status"] == "extracted" and man["captures"][cid]["source"] == "release"
    assert man["captures"][cid]["departures_status"] == "ok"  # the host capture before it is the previous one
    # a release manifest that is not complete is not extracted
    blobs[mp] = json.dumps({"state": "partial"}).encode()
    entries[-1]["sha256"] = _sha(blobs[mp])
    rel2 = d.ReleaseCopies(tmp_path / "scr2", catalogue=_catalogue(tmp_path / "xx", entries), restore=restore)
    d.run_closewin(snap, tmp_path / "none", tmp_path / "r3", mode="backfill", since=S0, catalogue=_catalogue(tmp_path / "xx", entries), release=rel2)
    assert json.loads((tmp_path / "r3" / "manifest.json").read_text())["captures"][cid]["reason"] == "release_manifest_not_complete"



# ---- freeze-check fixes 6-11, 14 ---------------------------------------------------------------------------------


def test_rules_doc_covers_functions_constants_and_readable_text(tmp_path):
    doc = d.series_rules_doc()
    assert {"constants", "funcs_sha256", "rule_text", "rule_text_sha256", "cadence_bounds_sha256", "horizons_sha256"} <= set(doc)
    assert doc["constants"]["PSEUDO_GAP_H"] == 6.0 and doc["constants"]["TEMP_RE"].startswith("^(Highest|Lowest)")
    assert "union over origins" in doc["rule_text"]
    p = tmp_path / "r.json"
    d.write_series_rules(p)
    p.write_text(json.dumps({**doc, "rule_text": doc["rule_text"] + " x"}))
    with pytest.raises(d.Refused):
        d.require_series_rules(p, require_committed=False)


def test_union_window_covers_both_origins_and_lagged_resolution():
    t0 = ep("2026-03-02T12:00:00Z")
    alt = t0 - 3 * 86400  # closedTime far after endDate + 1h (resolution lag)
    a, b, spans = d.union_window(t0, alt, 12.0)
    assert a == int(min(s_[0] for s_ in spans)) and b == int(max(s_[1] for s_ in spans))
    assert a <= alt - 21 * 3600 and b >= t0 + 14 * 3600  # both origins' windows are inside the union


def test_series_fetch_stores_coverage_predecessor_and_union(tmp_path):
    net = series_net()
    m = series_kw(tmp_path, net)
    assert m["status"] == "series_fetch_complete"
    rdir = tmp_path / "hist" / "h7_cb4_series"
    prog = [json.loads(line) for line in (rdir / "progress.jsonl").read_text().splitlines()]
    assert prog and all(p["covers_t0"] and p["covers_alt"] for p in prog)
    assert all(p["pred"]["price_points"] >= 0 and p["pred"]["trades"] >= 1 for p in prog)
    p0 = prog[0]
    assert (rdir / "pred_prices" / f"{p0['pred_file']}.csv.gz").exists() and (rdir / "pred_trades" / f"{p0['pred_file']}.csv.gz").exists()
    og = pd.read_csv(rdir / "outcomes_guarded.csv.gz", dtype=str, keep_default_na=False)
    assert {"pred_market_id", "pred_token_index"} <= set(og.columns) and (og.pred_market_id != "").all()
    u = d._load_jsonl_gz(rdir / "units.jsonl.gz")[0]
    assert u["pred_markets"] and "pred_token_index" not in u
    # a window cut by the cap is reported, not silently accepted
    net2 = series_net()
    tmp2 = tmp_path / "cap"
    tmp2.mkdir()
    series_kw(tmp2, net2, cap_at="2026-03-05")
    prog2 = [json.loads(line) for line in (tmp2 / "hist" / "h7_cb4_series" / "progress.jsonl").read_text().splitlines()]
    assert any(not p["covers_t0"] for p in prog2)


def test_group_s_amendment_required_matches_frame_and_decides_groups(tmp_path):
    net = era_net()
    m = era_kw(tmp_path, net, stage="frame")
    assert m["status"] == "era_frame_complete" and m["complete"] is False
    rdir = tmp_path / "hist" / "h7_cb4_era"
    fr = json.loads((rdir / "frame_report.json").read_text())
    assert "P0|sports" in fr["rules"]["kept_by_period_category"] and "P0|crypto" in fr["rules"]["kept_by_period_category"]
    assert not (rdir / "sample.csv.gz").exists() and fr["rules"]["kept_by_cell"] == {}
    am = tmp_path / "am.json"
    kw = dict(auto_frame=False, amendment_file=am)

    def run(**k):
        return era_kw(tmp_path, net, **{**kw, **k})

    # base helper overrides amendment_file when a frame exists; call era_fetch directly for refusal cases
    def direct(path):
        base = dict(seed="s", per_cell=3, periods=[("P0", ep("2026-03-01"), ep("2026-03-05"))], exclude_runs=["h2_main"],
                    h5_seal_copies=[_h5_copy(tmp_path, ("100",))], key=KEY, now=NOW, wall_clock=_wall(), sleep=lambda s: None,
                    live_check=None, windows_per_day=96, window_minutes=15, disk_cap=10**8, require_committed=False,
                    amendment_file=path)
        return d.era_fetch(tmp_path / "hist", "h7_cb4_era", net, **base)

    with pytest.raises(d.Refused, match="not found"):
        direct(am)
    sha = h5_seal.sha256_file(rdir / "frame_report.json")
    for doc, msg in (({"decision": "maybe", "sports_fee_categories": ["sports"], "era_frame_report_sha256": sha}, "decision"),
                     ({"decision": "as_declared", "sports_fee_categories": ["sports", "x"], "era_frame_report_sha256": sha}, "as_declared"),
                     ({"decision": "as_declared", "sports_fee_categories": ["sports"], "era_frame_report_sha256": "0"}, "does not match")):
        am.write_text(json.dumps(doc))
        with pytest.raises(d.Refused, match=msg):
            direct(am)
    assert not (rdir / "sample.csv.gz").exists()
    # an amended decision that adds a category to S changes the groups
    am.write_text(json.dumps({"decision": "amended", "sports_fee_categories": ["sports", "crypto"], "era_frame_report_sha256": sha}))
    m = direct(am)
    assert m["status"] == "era_fetch_complete"
    sample = pd.read_csv(rdir / "sample.csv.gz", dtype=str, keep_default_na=False)
    assert set(sample.group) == {"S"} and json.loads((rdir / "sample_report.json").read_text())["cells"]["S|P0"]["eligible"] == 9


def test_failed_requests_fail_the_item_not_an_empty_file(tmp_path):
    net = era_net()
    era_kw(tmp_path, net, stage="frame")
    net.fail_trades = True
    m = era_kw(tmp_path, net)
    rdir = tmp_path / "hist" / "h7_cb4_era"
    prog = [json.loads(line) for line in (rdir / "progress.jsonl").read_text().splitlines()]
    assert prog and all(p["status"] == "failed" and "trades status 404" in p["error"] for p in prog)
    assert m["counts"]["items_failed"] == 6 and m["counts"].get("items_done", 0) == 0
    assert not list((rdir / "prices").glob("*.csv.gz")) and not list((rdir / "trades").glob("*.csv.gz"))
    # a failed price request likewise fails the market (no empty price file marked done)
    net2 = era_net()
    tmp2 = tmp_path / "b"
    tmp2.mkdir()
    era_kw(tmp2, net2, stage="frame")
    net2.fail_price_tokens = {f"t{200 + i}a" for i in range(5)} | {f"t{100 + i}a" for i in range(4)}
    era_kw(tmp2, net2)
    prog2 = [json.loads(line) for line in (tmp2 / "hist" / "h7_cb4_era" / "progress.jsonl").read_text().splitlines()]
    failed2 = [p for p in prog2 if p["status"] == "failed"]
    assert failed2 and all("prices-history status 404" in p["error"] for p in failed2)
    assert not any((tmp2 / "hist" / "h7_cb4_era" / "prices" / f"{p['market_id']}.csv.gz").exists() for p in failed2)


def test_strict_price_and_trade_helpers_raise_on_non_200():
    net = FakeNet()
    net.fail_price_tokens = {"tok"}
    net.fail_trades = True
    lim = hb_mod().Limiter(net, rps=4.0, sleep=lambda s: None)
    with pytest.raises(d.ApiError):
        d.fetch_prices_strict(lim, "tok", 0, 1000)
    with pytest.raises(d.ApiError):
        d.fetch_trades_strict(lim, "c", KEY, 100)
    ok = d.fetch_prices_strict(lim, "other", 0, 10_000)
    assert len(ok) == 3


def test_failed_frame_window_is_counted_and_retried_not_capped(tmp_path):
    net = era_net()
    net.fail_markets = True
    m = era_kw(tmp_path, net, stage="frame")
    assert m["stopped"].startswith("walk_failed") and m["transient"] is True
    net.fail_markets = False
    m = era_kw(tmp_path, net, stage="frame")  # the failed day is retried and the frame completes
    assert m["status"] == "era_frame_complete"
    rep = json.loads((tmp_path / "hist" / "h7_cb4_era" / "frame_report.json").read_text())
    assert rep["windows_failed"] == 0 and rep["windows_dropped_capped"] == {"closed": 0, "active": 0}
    # persistent failure: after MAX_DAY_ATTEMPTS the day is recorded with failed windows COUNTED (visible), not as capped
    net3 = era_net()
    net3.fail_markets = True
    tmp3 = tmp_path / "c"
    tmp3.mkdir()
    res = [era_kw(tmp3, net3, stage="frame") for _ in range(12)]
    fin = next(r for r in res if r.get("status") == "era_frame_complete")
    rep3 = json.loads((tmp3 / "hist" / "h7_cb4_era" / "frame_report.json").read_text())
    assert rep3["windows_failed"] > 0 and rep3["windows_dropped_capped"] == {"closed": 0, "active": 0} and fin


def test_missing_exclusion_sample_is_a_refusal_not_a_disk_error(tmp_path, capsys):
    net = era_net()
    with pytest.raises(d.Refused, match="no .*sample.csv.gz"):
        d.era_fetch(tmp_path / "hist", "h7_cb4_era", net, exclude_runs=["h1_first"], key=KEY, now=NOW, wall_clock=_wall(), live_check=None)
    seal = _h5_copy(tmp_path)
    (tmp_path / "dd").mkdir()
    rc = d.cmd_fetch(_ns(transport=net, root=str(tmp_path / "hist"), exclude_seal_ids=str(seal), data_dumps=str(tmp_path / "dd"),
                         exclude_runs="h1_first", wall_clock=_wall(), now=NOW), require_committed=False, allow_nondeclared=True)
    assert rc == 2 and "h1_first" in capsys.readouterr().out
    # the ladders seal copy is required too
    (seal.parent / "h5_cb1_ladders_SEAL.json").unlink()
    rc = d.cmd_fetch(_ns(transport=net, root=str(tmp_path / "hist"), exclude_seal_ids=str(seal), data_dumps=str(tmp_path / "dd"),
                         wall_clock=_wall(), now=NOW), require_committed=False, allow_nondeclared=True)
    assert rc == 2 and "ladders" in capsys.readouterr().out


def test_h5_ladders_ids_are_excluded(tmp_path):
    ids = d._h5_ids(d.with_ladders_copy([_h5_copy(tmp_path, ("100",))]))
    assert ids == {"100", "L777"}


def test_record_deadline_before_and_after_t_seal(tmp_path, capsys):
    root = tmp_path / "hist"
    ns = types.SimpleNamespace(root=str(root), seals_dir=str(tmp_path / "s"), wall_clock=_wall())
    assert d.cmd_record_deadline(ns) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["deadline_recorded"] is False and "not_yet" in out and not root.exists()
    # an incomplete era run, a complete series run (left for q0083) and nothing else
    era_kw(tmp_path, era_net(), should_stop=lambda: True)
    series_kw(tmp_path, series_net())
    ns.wall_clock = _wall(d.T_SEAL_EPOCH + 1)
    assert d.cmd_record_deadline(ns) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["deadline_recorded"] is True and out["states"] == {"h7_cb4_era": "not_run", "h7_cb4_series": "complete"}
    assert (tmp_path / "s" / "h7_cb4_era_NOT_RUN.json").exists() and not (tmp_path / "s" / "h7_cb4_series_NOT_RUN.json").exists()
    assert d.cmd_record_deadline(ns) == 0  # idempotent


def test_event_weather_by_fee_category_and_shared_events_counted():
    def ev(eid, sid, fee="crypto", end=0, mkt=None):
        return {"event_id": eid, "end_epoch": 1.7e9 + end * 86400, "created_epoch": 1.7e9 + end * 86400 - 86400 * 2, "weather_title": 0,
                "series": [{"id": sid, "slug": sid}], "n_markets": 1, "closed_mode": True,
                "markets": [{"market_id": mkt or f"M{eid}", "condition_id": "c", "token0": "a", "token1": "b", "group_title": None,
                             "outcomes": ["Up", "Down"], "created_epoch": 1.7e9, "fee_category": fee, "neg_risk": 0}]}

    def g(eid, end):
        return {"event_id": eid, "event_closed": True, "markets": [{"market_id": f"M{eid}", "outcome_prices": '["1","0"]', "closed": True,
                                                                     "closed_time": iso(1.7e9 + end * 86400 + 3600)}]}

    evs = {}
    gs = {}
    for k in range(6):  # series A daily, event 'a2' also belongs to series B
        e = ev(f"a{k}", "A", end=k)
        evs[e["event_id"]] = e
        gs[e["event_id"]] = g(e["event_id"], k)
    evs["a2"]["series"].append({"id": "B", "slug": "B"})
    for k in range(6):
        if k != 2:
            e = ev(f"b{k}", "B", end=k)
            evs[e["event_id"]] = e
            gs[e["event_id"]] = g(e["event_id"], k)
    # a weather event by fee category (title does not match TEMP_RE)
    evs["a4"]["markets"][0]["fee_category"] = "weather"
    asm = d.assemble_units(evs, gs, seed="s", n_series=10, n_sports=0, members=31, r_from=1.7e9 - 1, r_to=1.7e9 + 20 * 86400,
                           history_ids=set(), h5_ids=set())
    rep = asm["report"]
    assert rep["unit_drops"].get("excluded_event_weather", 0) >= 1
    assert rep["events_shared_across_series"] >= 1 and rep["units_in_shared_events"] >= 1
