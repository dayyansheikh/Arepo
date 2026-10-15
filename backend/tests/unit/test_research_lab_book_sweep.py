"""Book sweep tests with fake transports only (no network)."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import pandas as pd
import pytest

from astrolabe.research_lab import book_sweep as bs
from astrolabe.research_lab.extract import COLUMNS, market_row


def lvl(p, s):
    return {"price": p, "size": s}


def book(tid, bids=(), asks=(), **kw):
    return {"asset_id": tid, "market": "0xabc", "bids": list(bids), "asks": list(asks),
            "timestamp": "1760000000000", "hash": "h" + tid, "tick_size": "0.01",
            "min_order_size": "5", **kw}


class Fake:
    """Fake POST /books: returns two-sided books unless overridden."""

    def __init__(self, overrides=None, script=None):
        self.calls: list[list[str]] = []
        self.overrides = overrides or {}
        self.script = list(script or [])

    def __call__(self, body):
        toks = [b["token_id"] for b in body]
        self.calls.append(toks)
        if self.script:
            status, headers = self.script.pop(0)
            if status != 200:
                return status, b"", headers
        out = []
        for t in toks:
            if t in self.overrides:
                if self.overrides[t] is not None:
                    out.append(self.overrides[t])
            else:
                out.append(book(t, [lvl("0.40", "10")], [lvl("0.45", "20")]))
        return 200, json.dumps(out).encode(), {}


def toks(n):
    return [(f"{i:03d}", f"m{i}") for i in range(n)]


def run(tmp_path, tokens, transport, **kw):
    kw.setdefault("sleep", lambda s: None)
    return bs.run_sweep(tokens, transport, out_root=tmp_path / "out", **kw)


def read_rows(tmp_path, m):
    return pd.read_csv(tmp_path / "out" / m["sweep_id"] / "rows.csv.gz", dtype=str)


def test_batching_and_order_determinism(tmp_path):
    t = toks(250)
    shuffled = sorted(t, reverse=True)
    f1, f2 = Fake(), Fake()
    m1 = run(tmp_path, sorted(shuffled), f1)
    m2 = run(tmp_path, t, f2)
    assert [len(c) for c in f1.calls] == [100, 100, 50]
    assert f1.calls == f2.calls
    assert f1.calls[0] == sorted(f1.calls[0])
    assert m1["state"] == "complete" and m1["tokens_returned"] == 250
    rows = read_rows(tmp_path, m1)
    assert list(rows["token_id"]) == [x[0] for x in t]
    assert [b["tokens_requested"] for b in m1["batches"]] == [100, 100, 50]
    assert m2["batches"][0]["sha256"] == m1["batches"][0]["sha256"]
    assert {"request_sent_utc", "received_utc", "status", "sha256"} <= set(m1["batches"][0])


def test_select_tokens_sorted_and_eligibility():
    n = 4
    df = pd.DataFrame({c: [None] * n for c in COLUMNS})
    df["market_id"] = ["1", "2", "3", "4"]
    df["binary"] = 1
    df["closed"], df["active"] = "False", "True"
    df["best_bid"], df["best_ask"], df["spread"] = 0.4, 0.45, 0.05
    df["received_utc"] = "2026-10-10T19:00:00.000000Z"
    df["end_date"] = [None, "2026-10-10T20:00:00Z", "2026-10-11T00:00:00Z", None]
    df["clob_token_id_0"] = ["9", "8", "7", None]
    got = bs.select_tokens(df)
    assert got == [("7", "3"), ("9", "1")]  # 2 ends within 3h; 4 has no token
    with pytest.raises(ValueError):
        bs.select_tokens(df.drop(columns=["clob_token_id_0"]))


def test_market_row_has_token():
    ids = '["123456789012345678901234567890","2"]'
    m = {"id": 1, "outcomes": '["Yes","No"]', "clobTokenIds": ids}
    assert market_row(m, "c", "s", "t")["clob_token_id_0"] == "123456789012345678901234567890"
    assert market_row({"id": 2}, "c", "s", "t")["clob_token_id_0"] is None


def test_level_sorting_and_depth_unsorted():
    b = book("x",
             bids=[lvl("0.35", "7"), lvl("0.40", "10"), lvl("0.395", "3"), lvl("0.30", "100")],
             asks=[lvl("0.60", "50"), lvl("0.45", "20"), lvl("0.46", "4"), lvl("0.50", "1")])
    r = bs.parse_book(b)
    assert (r["best_bid"], r["best_ask"]) == (0.40, 0.45)
    assert (r["bid_size_1"], r["ask_size_1"]) == (10.0, 20.0)
    assert r["depth_bid_1c"] == 13.0 and r["depth_ask_1c"] == 24.0
    assert r["depth_bid_5c"] == 20.0 and r["depth_ask_5c"] == 25.0  # 0.35 and 0.50 inclusive
    assert (r["n_bid_levels"], r["n_ask_levels"]) == (4, 4)
    assert r["state"] == "two_sided"
    assert r["book_timestamp"] == "1760000000000" and r["book_hash"] == "hx"
    assert r["tick_size"] == "0.01" and r["min_order_size"] == "5"


def test_states(tmp_path):
    t = [("a", "1"), ("b", "2"), ("c", "3"), ("d", "4"), ("e", "5")]
    f = Fake(overrides={
        "b": book("b", bids=[lvl("0.2", "5")]),
        "c": book("c"),
        "d": None,
        "e": book("e", asks=[lvl("0.9", "5"), lvl("bad", "1"), lvl("0.8", "0")]),
    })
    m = run(tmp_path, t, f)
    rows = read_rows(tmp_path, m).set_index("token_id")
    assert rows.loc["a", "state"] == "two_sided"
    assert rows.loc["b", "state"] == "one_sided" and pd.isna(rows.loc["b", "best_ask"])
    assert rows.loc["c", "state"] == "empty"
    assert rows.loc["d", "state"] == "missing_from_response"
    assert rows.loc["e", "state"] == "one_sided" and rows.loc["e", "n_ask_levels"] == "1"
    assert m["tokens_returned"] == 4 and m["state"] == "complete"


def test_retry_on_429_then_success(tmp_path):
    waits = []
    f = Fake(script=[(429, {"Retry-After": "2"}), (503, {}), (200, {})])
    m = run(tmp_path, toks(5), f, sleep=waits.append)
    assert m["state"] == "complete" and m["request_count"] == 3
    assert m["batches"][0]["attempts"] == 3 and m["batches"][0]["status"] == 200
    assert waits[0] == 2.0 and len(waits) == 2


def test_retries_exhausted_is_incomplete(tmp_path):
    f = Fake(script=[(429, {})] * 10)
    m = run(tmp_path, toks(5), f)
    assert m["state"].startswith("incomplete:") and m["request_count"] == 6
    assert m["rows_written"] == 0


def test_request_cap_incomplete(tmp_path, monkeypatch):
    monkeypatch.setattr(bs, "MAX_REQUESTS", 2)
    m = run(tmp_path, toks(500), Fake())
    assert m["state"] == "incomplete:max_requests@batch_2"
    assert m["rows_written"] == 200 and m["tokens_attempted"] == 200


def test_time_cap_incomplete(tmp_path, monkeypatch):
    monkeypatch.setattr(bs, "MAX_SECONDS", 10)
    ticks = iter([0, 1, 100, 200, 300, 400])
    m = run(tmp_path, toks(500), Fake(), clock=lambda: next(ticks))
    assert m["state"].startswith("incomplete:max_seconds")


def test_atomic_output_and_no_raw_by_default(tmp_path):
    m = run(tmp_path, toks(3), Fake())
    out = tmp_path / "out"
    assert [p.name for p in out.iterdir()] == [m["sweep_id"]]
    assert not (out / m["sweep_id"] / "raw").exists()
    m2 = run(tmp_path, toks(3), Fake(), keep_raw=True)
    raw = out / m2["sweep_id"] / "raw" / "batch_00000.json.gz"
    assert json.loads(gzip.open(raw).read())[0]["asset_id"] == "000"


def test_failure_leaves_no_partial_dir(tmp_path):
    def boom(body):
        raise RuntimeError("x")

    with pytest.raises(RuntimeError):
        run(tmp_path, toks(3), boom)
    assert list((tmp_path / "out").iterdir()) == []


def make_snapshot(d: Path) -> Path:
    d.mkdir(parents=True)
    n = 3
    df = pd.DataFrame({c: [None] * n for c in COLUMNS})
    df["market_id"] = ["1", "2", "3"]
    df["binary"] = 1
    df["closed"], df["active"] = "False", "True"
    df["best_bid"], df["best_ask"], df["spread"] = 0.4, 0.45, 0.05
    df["received_utc"] = "2026-10-10T19:00:00.000000Z"
    df["clob_token_id_0"] = [
        "71321045679252212594626385532706912750332728571942532289631379312455583992563",
        "2", "1",
    ]
    df.to_csv(d / "rows.csv.gz", index=False)
    (d / "manifest.json").write_text(json.dumps({"capture_id": "snap1", "state": "complete"}))
    return d


def test_series_linkage_and_big_token_ids(tmp_path):
    snap = make_snapshot(tmp_path / "snap")
    f = Fake()
    res = bs.run_series(snap, f, repeat=3, out_root=tmp_path / "out", sleep=lambda s: None)
    assert len(res) == 3 and len({m["sweep_id"] for m in res}) == 3
    assert len({m["series_id"] for m in res}) == 1
    assert [m["series_index"] for m in res] == [0, 1, 2]
    assert all(m["snapshot_id"] == "snap1" and len(m["snapshot_manifest_sha256"]) == 64
               for m in res)
    assert f.calls[0] == f.calls[1] == f.calls[2]
    assert f.calls[0][0] == "1" and f.calls[0][-1].startswith("7132104567925221259")
    assert f.calls[0][-1].endswith("992563")  # not mangled through float


def test_incomplete_snapshot_refused(tmp_path):
    snap = make_snapshot(tmp_path / "snap")
    (snap / "manifest.json").write_text(json.dumps({"state": "incomplete:x"}))
    with pytest.raises(ValueError):
        bs.load_tokens(snap)
