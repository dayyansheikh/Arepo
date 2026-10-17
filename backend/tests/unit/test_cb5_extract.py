# ruff: noqa: E501
"""CB5-F extractor tables: listings/ and cdf/ (astrolabe.research_lab.cb5_extract)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

from astrolabe.research_lab import cb5_extract as x

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_cb4_data import _ext, _row, make_capture, make_sweep  # noqa: E402

S0, S1, S2 = "2026-10-12T00:00:00Z", "2026-10-12T02:00:00Z", "2026-10-12T04:00:00Z"
OLD = "2026-09-01T00:00:00Z"
NEW1 = "2026-10-12T01:30:00Z"  # created in the 6h before S1
NEW2 = "2026-10-12T03:30:00Z"
FAR = "2026-12-01T00:00:00Z"


def _family_list(path: Path, fams) -> Path:
    doc = {"version": 1, "families": fams}
    doc["sha256"] = x.family_list_sha256(doc)
    path.write_text(json.dumps(doc))
    return path


def _caps(tmp_path):
    snap = tmp_path / "snap"
    make_capture(snap, "c0", S0, [_row("1", FAR), _row("2", FAR)], [_ext("1", OLD), _ext("2", OLD)])
    make_capture(snap, "c1", S1, [_row("1", FAR), _row("2", FAR), _row("3", FAR)],
                 [_ext("1", OLD), _ext("2", OLD), _ext("3", NEW1)])
    make_capture(snap, "c2", S2, [_row("1", FAR), _row("2", FAR), _row("3", FAR), _row("4", FAR)],
                 [_ext("1", OLD), _ext("2", OLD), _ext("3", NEW1), _ext("4", NEW2)])
    return snap


def _run(tmp_path, snap, **kw):
    return x.run_tables(snap, tmp_path / "sweeps", tmp_path / "cb5", mode="backfill", since=S0, git_commit="t", **kw)


def test_listings_first_sightings_only_and_chain(tmp_path):
    snap = _caps(tmp_path)
    res = _run(tmp_path, snap, tables=("listings",))
    assert res["written"] == 3 and res["backfill_complete"]
    c1 = x.read_table(tmp_path / "cb5", "listings", "c1")
    assert list(c1["market_id"]) == ["3"] and c1["first_seen_certain"].iloc[0] == "1"
    c2 = x.read_table(tmp_path / "cb5", "listings", "c2")
    assert list(c2["market_id"]) == ["4"]  # market 3 was already in c1's listing: not a first sighting
    c0 = x.read_table(tmp_path / "cb5", "listings", "c0")
    assert len(c0) == 0  # created long before the 6h window
    assert not any("outcome" in c for c in c1.columns)


def test_idempotent_and_no_outcome_columns(tmp_path):
    snap = _caps(tmp_path)
    _run(tmp_path, snap, tables=("listings",))
    res = _run(tmp_path, snap, tables=("listings",))
    assert res["written"] == 0 and res["remaining"] == 0
    x.assert_no_outcome_columns(x.LISTINGS_COLUMNS + x.CDF_COLUMNS)
    with pytest.raises(AssertionError):
        x.assert_no_outcome_columns(["market_id", "outcome_prices"])


def test_broken_chain_marks_first_seen_uncertain(tmp_path):
    snap = _caps(tmp_path)
    # run only c1 and c2 (since after c0): the chain starts uncertain
    res = x.run_tables(snap, tmp_path / "sweeps", tmp_path / "cb5", mode="backfill", since=S1, tables=("listings",), git_commit="t")
    assert res["written"] == 2
    c1 = x.read_table(tmp_path / "cb5", "listings", "c1")
    assert c1["first_seen_certain"].iloc[0] == "0"
    c2 = x.read_table(tmp_path / "cb5", "listings", "c2")
    assert c2["first_seen_certain"].iloc[0] == "1"


def test_cdf_prospective_versioning(tmp_path):
    snap = _caps(tmp_path)
    fl = _family_list(tmp_path / "fam.json", [{"family_id": "F1", "listed_utc": "2026-10-12T01:00:00Z", "market_ids": ["1", "3"]}])
    res = _run(tmp_path, snap, tables=("cdf",), family_list=fl)
    assert res["written"] == 3
    assert len(x.read_table(tmp_path / "cb5", "cdf", "c0")) == 0  # family listed after c0
    c1 = x.read_table(tmp_path / "cb5", "cdf", "c1")
    assert sorted(c1["market_id"]) == ["1", "3"] and set(c1["family_ids"]) == {"F1"}


def test_family_list_hash_enforced(tmp_path):
    fl = _family_list(tmp_path / "fam.json", [{"family_id": "F1", "listed_utc": S0, "market_ids": ["1"]}])
    doc = json.loads(fl.read_text())
    doc["families"][0]["market_ids"].append("2")
    fl.write_text(json.dumps(doc))
    with pytest.raises(ValueError):
        x.load_family_list(fl)


def test_headroom_refusal_and_missing_capture(tmp_path):
    snap = _caps(tmp_path)
    res = _run(tmp_path, snap, tables=("listings",), data_dumps=tmp_path, data_dumps_max_gb=0.0, dir_gb=lambda p: 5.0)
    assert res["stopped"] == "refused_data_dumps_over_cap" and res["written"] == 0
    make_capture(snap, "c3", "2026-10-12T06:00:00Z", [], with_files=False)
    res = _run(tmp_path, snap, tables=("listings",))
    assert res["missing"] == 1 and res["written"] == 3
    man = json.loads((tmp_path / "cb5" / "manifest.json").read_text())
    assert man["captures"]["c3"]["tables"]["listings"]["status"] == "missing"
    assert man["chain"] is not None and man["chain"]["capture_id"] == "c2"  # a missing capture never resets the chain


def test_missing_capture_retries_do_not_break_later_chain(tmp_path):
    snap = _caps(tmp_path)
    make_capture(snap, "c3", "2026-10-12T06:00:00Z", [], with_files=False)
    make_capture(snap, "c4", "2026-10-12T08:00:00Z", [_row("1", FAR), _row("5", FAR)], [_ext("1", OLD), _ext("5", "2026-10-12T07:30:00Z")])
    kw = dict(tables=("listings",), mode="all-new", since=S0, git_commit="t")
    x.run_tables(snap, tmp_path / "sweeps", tmp_path / "cb5", **kw)
    make_capture(snap, "c5", "2026-10-12T10:00:00Z", [_row("1", FAR), _row("5", FAR), _row("6", FAR)],
                 [_ext("1", OLD), _ext("5", "2026-10-12T07:30:00Z"), _ext("6", "2026-10-12T09:30:00Z")])
    res = x.run_tables(snap, tmp_path / "sweeps", tmp_path / "cb5", **kw)  # c3 stays missing and is retried first
    assert res["missing"] == 1
    c5 = x.read_table(tmp_path / "cb5", "listings", "c5")
    assert list(c5["market_id"]) == ["6"] and c5["first_seen_certain"].iloc[0] == "1"
    c4 = x.read_table(tmp_path / "cb5", "listings", "c4")
    assert c4["first_seen_certain"].iloc[0] == "0"  # predecessor c3 is missing: uncertain by adjacency


def test_neg_risk_members_counted_at_sighting_over_full_capture(tmp_path):
    snap = tmp_path / "snap"
    make_capture(snap, "c0", S0, [_row("1", FAR), _row("2", FAR)],
                 [_ext("1", OLD, neg_risk_market_id="G"), _ext("2", OLD, neg_risk_market_id="G")])
    make_capture(snap, "c1", S1, [_row("1", FAR), _row("2", FAR),
                                  _row("3", FAR)], [_ext("1", OLD, neg_risk_market_id="G"), _ext("2", OLD, neg_risk_market_id="G"), _ext("3", NEW1, neg_risk_market_id="G")])
    _run(tmp_path, snap, tables=("listings",))
    c1 = x.read_table(tmp_path / "cb5", "listings", "c1")
    assert list(c1["neg_risk_n_members_at_sighting"]) == ["3"]  # earlier-listed members counted, none later
    assert "sweep_batch_receipt_utc" in c1.columns


def test_sweep_touch_joined(tmp_path):
    snap = _caps(tmp_path)
    sw = tmp_path / "sweeps"
    make_sweep(sw, "s1", "c1", 0, [{"market_id": "3", "batch_receipt_utc": S1, "state": "ok", "best_bid": "0.41", "best_ask": "0.44", "bid_size_1": "50", "ask_size_1": "60"}])
    _run(tmp_path, snap, tables=("listings",))
    c1 = x.read_table(tmp_path / "cb5", "listings", "c1")
    assert c1["sweep_ask_size_1"].iloc[0] == "60" and c1["sweep_best_bid"].iloc[0] == "0.41"


def test_cb1_cb2_extractor_untouched():
    from astrolabe.research_lab import creative_batch1 as cb

    assert cb.EXTRACTOR_VERSION == "cb1-extract-v2"
    assert "listings" not in cb.CB2_TABLES and "cdf" not in cb.CB2_TABLES
    assert isinstance(pd.DataFrame(), pd.DataFrame)
