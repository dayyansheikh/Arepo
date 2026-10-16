# ruff: noqa: E501
"""CB3 quote_state/ extractor (cb3_quote_state, scripts/run_cb3_quote_state.py; CREATIVE_BATCH_3.md §4.3.1)."""

from __future__ import annotations

import gzip
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

from astrolabe.research_lab import cb3_quote_state as q

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import run_cb3_quote_state as script  # noqa: E402

ROW_COLS = ["capture_id", "capture_start_utc", "received_utc", "market_id", "condition_id", "event_id",
            "closed", "active", "binary", "best_bid", "best_ask", "spread", "last_trade_price",
            "chg_1h", "chg_1d", "volume24hr", "end_date"]
EXT_COLS = ["capture_id", "market_id", "accepting_orders", "volume_num", "fee_schedule", "fee_category",
            "created_at", "neg_risk_market_id", "parent_event_ids", "series_slugs"]
SW_COLS = ["market_id", "batch_receipt_utc", "state", "best_bid", "best_ask", "bid_size_1", "ask_size_1",
           "depth_bid_1c", "depth_ask_1c"]
TIGHT = {"best_bid": "0.40", "best_ask": "0.45", "spread": "0.05"}
WIDE = {"best_bid": "0.10", "best_ask": "0.60", "spread": "0.5"}
CAPS = ["2026-10-12T00:00:00Z", "2026-10-12T06:00:00Z", "2026-10-12T12:00:00Z", "2026-10-12T18:00:00Z",
        "2026-10-13T00:00:00Z", "2026-10-13T06:00:00Z", "2026-10-13T12:00:00Z"]


def _gz(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", newline="") as fh:
        df.to_csv(fh, index=False)


def _row(cid, start, mid, **kw):
    r = dict.fromkeys(ROW_COLS, "")
    r.update(capture_id=cid, capture_start_utc=start, received_utc=start, market_id=mid, condition_id=f"c{mid}",
             event_id=f"E{mid}", closed="False", active="True", binary="1", last_trade_price="0.4200",
             volume24hr="123.50", chg_1d="0.0100", end_date="2027-01-01T00:00:00Z", **TIGHT)
    r.update(kw)
    return r


def make_capture(root: Path, cid: str, start: str, rows: list[dict], ext: list[dict] | None = None) -> None:
    d = root / cid
    _gz(d / "rows.csv.gz", pd.DataFrame(rows, columns=ROW_COLS))
    if ext is not None:
        _gz(d / "rows_ext.csv.gz", pd.DataFrame(ext, columns=EXT_COLS))
    (d / "manifest.json").write_text(json.dumps({"capture_id": cid, "started_utc": start, "state": "complete"}))


def make_sweep(root: Path, sid: str, cid: str, k: int, rows: list[dict]) -> None:
    d = root / sid
    _gz(d / "rows.csv.gz", pd.DataFrame(rows, columns=SW_COLS))
    (d / "manifest.json").write_text(json.dumps({"snapshot_id": cid, "series_index": k, "state": "complete",
                                                  "started_utc": f"2026-10-12T00:1{k}:00Z"}))


@pytest.fixture
def world(tmp_path):
    """7 captures. Market A: tight only at capture 0. B: always tight. C: never tight. N: non-binary, tight."""
    snap, sw, out = tmp_path / "snap", tmp_path / "sweeps", tmp_path / "cb3"
    for i, s in enumerate(CAPS):
        cid = f"cap{i}"
        rows = [_row(cid, s, "A", **(TIGHT if i == 0 else WIDE)), _row(cid, s, "B"),
                _row(cid, s, "C", **WIDE), _row(cid, s, "N", binary="0")]
        ext = None
        if i >= 4:
            ext = [dict.fromkeys(EXT_COLS, "") | {"capture_id": cid, "market_id": m, "accepting_orders": "1.0",
                                                  "volume_num": "1000.250", "fee_category": "politics",
                                                  "neg_risk_market_id": f"NR{m}"} for m in "ABCN"]
        make_capture(snap, cid, s, rows, ext)
    make_sweep(sw, "sw0", "cap5", 0, [dict.fromkeys(SW_COLS, "") | {
        "market_id": "B", "batch_receipt_utc": "T1", "state": "two_sided", "best_bid": "0.401",
        "best_ask": "0.451", "bid_size_1": "10.0", "ask_size_1": "11.0", "depth_bid_1c": "5.50",
        "depth_ask_1c": "6.0"}])
    return snap, sw, out


def _run(world, **kw):
    snap, sw, out = world
    kw.setdefault("mode", "backfill")
    kw.setdefault("before", "2026-10-15T21:00:00Z")
    kw.setdefault("git_commit", "abc")
    return q.run(snap, sw, out, **kw)


def _rows(out, i):
    return q.read_quote_state(out, f"cap{i}")


def _cli(world, *extra):
    return script.main(["--backfill-before", "2026-10-15T21:00Z", "--snapshot-root", str(world[0]),
                        "--sweep-root", str(world[1]), "--root", str(world[2]), *extra])


def test_membership_tight_at_c_or_previous_four(world):
    r = _run(world)
    out = world[2]
    assert r["written"] == 7 and r["backfill_complete"] is True
    ids = lambda i: set(_rows(out, i)["market_id"])  # noqa: E731
    assert ids(0) == {"A", "B"}  # A tight at 0, B always; C never; N not binary
    for i in (1, 2, 3, 4):  # A tight only at capture 0: row at c = 1..4
        assert "A" in ids(i)
    assert "A" not in ids(5)  # c-5
    assert "C" not in ids(6) and "N" not in ids(6)
    row = _rows(out, 4).set_index("market_id").loc["A"]
    assert row["tight"] == "0" and row["tight_mask_prev4"] == "1000"
    assert _rows(out, 0).set_index("market_id").loc["A"]["tight_mask_prev4"] == "????"


def test_ids_file_lists_every_binary_market_sorted(world):
    _run(world)
    ids = q.read_quote_state(world[2], "cap6", ids=True)
    assert list(ids.columns) == ["market_id"] and list(ids["market_id"]) == ["A", "B", "C"]


def test_manifest_membership_complete_flag_and_counts(world):
    _run(world)
    man = json.loads((world[2] / "manifest.json").read_text())
    assert man["extractor_version"] == q.EXTRACTOR_VERSION
    assert man["captures"]["cap0"]["membership_complete"] is False
    assert man["captures"]["cap3"]["membership_complete"] is False
    assert man["captures"]["cap4"]["membership_complete"] is True
    e = man["captures"]["cap5"]
    assert e["n_ids"] == 3 and e["n_tight"] == 2 and e["n_sweeps_found"] == 1 and e["mode"] == "backfill"
    assert {"csv", "ids"} <= set(e["sha256"]) and "rows" in e["source_sha256"] and "sweep_1" in e["source_sha256"]


def test_values_copied_exactly_and_blank_before_sidecar(world):
    _run(world)
    out = world[2]
    r0 = _rows(out, 0).set_index("market_id").loc["B"]
    assert r0["last_trade_price"] == "0.4200" and r0["volume24hr"] == "123.50" and r0["spread"] == "0.05"
    assert r0["accepting_orders"] == "" and r0["volume_num"] == "" and r0["s1_best_bid"] == ""
    r5 = _rows(out, 5).set_index("market_id").loc["B"]
    assert r5["accepting_orders"] == "1.0" and r5["volume_num"] == "1000.250" and r5["neg_risk_id"] == "NRB"
    assert r5["s1_best_bid"] == "0.401" and r5["s1_depth_bid_1c"] == "5.50" and r5["s2_best_bid"] == ""
    assert list(_rows(out, 5).columns) == q.ALL_COLUMNS


def test_idempotent_rerun_writes_nothing(world):
    _run(world)
    out = world[2]
    files = sorted(p for p in out.rglob("*") if p.is_file() and p.name != ".lock")
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    r = _run(world)
    assert r["written"] == 0 and r["backfill_complete"] is True
    assert before == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def test_crash_rerun_completes_only_missing(world):
    r = _run(world, budget_s=0.0)
    assert r["stopped"] == "budget" and r["written"] == 0 and r["backfill_complete"] is False
    r = _run(world)
    assert r["written"] == 7


def test_version_mismatch_refuses(world):
    _run(world)
    mp = world[2] / "manifest.json"
    man = json.loads(mp.read_text())
    man["extractor_version"] = "cb3-quote-state-v0"
    mp.write_text(json.dumps(man))
    with pytest.raises(q.VersionMismatch):
        _run(world)
    assert _cli(world) == 1


def test_data_dumps_cap_refuses_and_exits_nonzero(world, tmp_path, capsys):
    dumps = tmp_path / "dd"
    dumps.mkdir()
    (dumps / "f").write_bytes(b"x" * 2_000_000)
    r = _run(world, data_dumps=dumps, data_dumps_max_gb=0.001)
    assert r["stopped"] == "refused_data_dumps_over_cap" and r["written"] == 0 and r["backfill_complete"] is False
    assert not (world[2] / "manifest.json").exists()
    rc = _cli(world, "--data-dumps", str(dumps), "--data-dumps-max-gb", "0.001")
    assert rc == 1 and "refused_data_dumps_over_cap" in capsys.readouterr().out


def test_data_dumps_exceeded_between_captures_stops(world, tmp_path):
    calls = {"n": 0}

    def gb(_p):
        calls["n"] += 1
        return 0.0 if calls["n"] <= 3 else 99.0

    r = _run(world, data_dumps=tmp_path, data_dumps_max_gb=10.5, dir_gb=gb)
    assert r["stopped"] == "data_dumps_over_cap" and 0 < r["written"] < 7


def test_own_disk_cap_stops(world):
    r = _run(world, disk_cap_gb=0.0)
    assert r["stopped"] == "disk_cap" and r["written"] == 0


def test_backfill_before_excludes_bound_and_rejects_later_bound(world):
    r = _run(world, before="2026-10-12T12:00:00Z")
    assert r["written"] == 2 and r["backfill_complete"] is True  # cap0, cap1; the bound capture cap2 is excluded
    assert not (world[2] / "quote_state" / "cap2.csv.gz").exists()
    with pytest.raises(q.WindowError):
        _run(world, before="2026-10-16T00:00:00Z")
    with pytest.raises(q.WindowError):
        _run(world, before=None)


def test_j4r_capture_never_read_by_backfill(world):
    make_capture(world[0], "capJ", "2026-10-16T06:00:00Z", [_row("capJ", "2026-10-16T06:00:00Z", "B")])
    (world[0] / "capJ" / "rows.csv.gz").write_bytes(b"not a gzip file")  # any read would raise
    r = _run(world)
    assert r["written"] == 7 and not (world[2] / "quote_state" / "capJ.csv.gz").exists()


def test_all_new_covers_j4r_newest_first(world):
    make_capture(world[0], "capJ", "2026-10-16T06:00:00Z", [_row("capJ", "2026-10-16T06:00:00Z", "B")])
    r = _run(world, mode="all-new", before=None)
    assert r["written"] == 8 and (world[2] / "quote_state" / "capJ.csv.gz").exists()
    assert r["backfill_complete"] is False
    assert "A" in set(_rows(world[2], 4)["market_id"])  # membership independent of processing order


def test_missing_capture_recorded_and_run_continues(world):
    (world[0] / "cap2" / "rows.csv.gz").rename(world[0] / "cap2" / "moved_away")
    r = _run(world)
    assert r["missing"] == 1 and r["written"] == 6 and r["backfill_complete"] is True
    man = json.loads((world[2] / "manifest.json").read_text())
    assert man["captures"]["cap2"]["status"] == "missing"
    assert not (world[2] / "quote_state" / "cap2.csv.gz").exists()
    assert man["captures"]["cap3"]["membership_complete"] is False  # predecessor cap2 unavailable
    b3 = _rows(world[2], 3).set_index("market_id").loc["B"]["tight_mask_prev4"]
    assert b3 == "?11?"  # no 4th predecessor; cap2 rows gone
    r2 = _run(world)
    assert r2["written"] == 0 and r2["missing"] == 0  # recorded missing is not retried


def test_sweep_archived_leaves_blank(world):
    (world[1] / "sw0" / "rows.csv.gz").rename(world[1] / "sw0" / "moved_away")
    _run(world)
    man = json.loads((world[2] / "manifest.json").read_text())
    assert man["captures"]["cap5"]["n_sweeps_found"] == 0
    assert _rows(world[2], 5).set_index("market_id").loc["B"]["s1_best_bid"] == ""


def test_other_roots_untouched(world):
    snap, sw, _ = world

    def digest(root):
        return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob("*")) if p.is_file()}

    d0 = (digest(snap), digest(sw))
    _run(world)
    assert (digest(snap), digest(sw)) == d0  # read-only on snapshots and sweeps
    assert not list(world[2].parent.glob("cb1_extract")) and not list(world[2].parent.glob("cb2_extract"))


def test_script_summary_json_has_completion_flag(world, capsys):
    assert _cli(world) == 0
    assert '"backfill_complete": true' in capsys.readouterr().out
