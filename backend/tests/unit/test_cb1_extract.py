# ruff: noqa: E501
"""CB1 snapshot extractor (creative_batch1.extract, scripts/run_cb1_extract.py)."""

from __future__ import annotations

import gzip
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import creative_batch1 as cb
from astrolabe.research_lab import forecast

BACKEND = Path(__file__).resolve().parents[2]
ROW_COLS = ["capture_id", "capture_start_utc", "received_utc", "market_id", "condition_id", "event_id",
            "closed", "active", "binary", "best_bid", "best_ask", "spread", "last_trade_price",
            "chg_1h", "chg_1d", "chg_1w", "liquidity", "volume24hr", "end_date", "updated_at",
            "dup_count", "clob_token_id_0", "neg_risk", "neg_risk_market_id", "neg_risk_other",
            "event_neg_risk_augmented", "page_index"]
EXT_COLS = ["capture_id", "market_id", "accepting_orders", "fees_enabled", "volume_num",
            "fee_schedule", "fee_category"]


def _row(cid, mid, **kw):
    r = dict.fromkeys(ROW_COLS, "")
    r.update(capture_id=cid, capture_start_utc="2026-10-12T00:00:00Z",
             received_utc="2026-10-12T00:05:00Z", market_id=mid, event_id=f"E{mid}",
             closed="False", active="True", binary=1, best_bid=0.4, best_ask=0.45, spread=0.05,
             last_trade_price=0.42, end_date="2026-12-01T00:00:00Z", clob_token_id_0=f"tok{mid}")
    r.update(kw)
    return r


def _write_gz(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", newline="") as fh:
        df.to_csv(fh, index=False)


def make_capture(root: Path, cid: str, start: str, rows: list[dict], ext: list[dict] | None = None,
                 state="complete") -> Path:
    d = root / cid
    d.mkdir(parents=True)
    _write_gz(d / "rows.csv.gz", pd.DataFrame(rows, columns=ROW_COLS))
    if ext is not None:
        _write_gz(d / "rows_ext.csv.gz", pd.DataFrame(ext, columns=EXT_COLS))
        (d / "ext_manifest.json").write_text("{}")
    (d / "manifest.json").write_text(json.dumps({"capture_id": cid, "started_utc": start,
                                                  "state": state}))
    return d


def make_sweep(root: Path, sid: str, cid: str, k: int, asks: dict[str, tuple[float, float]]):
    d = root / sid
    d.mkdir(parents=True)
    _write_gz(d / "rows.csv.gz", pd.DataFrame(
        [{"market_id": m, "best_ask": a, "ask_size_1": s, "state": "two_sided"}
         for m, (a, s) in asks.items()]))
    (d / "manifest.json").write_text(json.dumps({"snapshot_id": cid, "series_index": k,
                                                  "state": "complete",
                                                  "started_utc": f"2026-10-12T00:1{k}:00Z"}))


def _ext(cid, mid, **kw):
    r = {"capture_id": cid, "market_id": mid, "accepting_orders": 1, "fees_enabled": 1,
         "volume_num": 1000.0, "fee_schedule": '{"rate":0.04,"exponent":1}', "fee_category": "politics"}
    r.update(kw)
    return r


@pytest.fixture
def world(tmp_path):
    snap, sw, ex = tmp_path / "snap", tmp_path / "sweeps", tmp_path / "extract"
    cid = "cap_a"
    rows = [
        _row(cid, "1", neg_risk_market_id="NR1", neg_risk=1, neg_risk_other=0, event_neg_risk_augmented=0),
        _row(cid, "2", neg_risk_market_id="NR1", neg_risk=1, neg_risk_other=0, event_neg_risk_augmented=0),
        _row(cid, "3"),  # plain market: dropped
        # post-end favourite (YES side, ask 0.97), end passed
        _row(cid, "4", best_bid=0.95, best_ask=0.97, end_date="2026-10-11T00:00:00Z"),
        # post-end NO favourite: mid 0.03, touch = 1 - bid = 0.97
        _row(cid, "5", best_bid=0.03, best_ask=0.05, end_date="2026-10-11T00:00:00Z"),
        # favourite but end in the future: dropped
        _row(cid, "6", best_bid=0.95, best_ask=0.97),
        # post-end but closed: dropped
        _row(cid, "7", best_bid=0.95, best_ask=0.97, end_date="2026-10-11T00:00:00Z", closed="True"),
        # post-end, touch below 0.95: dropped
        _row(cid, "8", best_bid=0.90, best_ask=0.92, end_date="2026-10-11T00:00:00Z"),
    ]
    ext = [_ext(cid, str(i)) for i in range(1, 9)]
    make_capture(snap, cid, "2026-10-12T00:00:00Z", rows, ext)
    make_sweep(sw, "sw_a1", cid, 0, {"1": (0.46, 10.0)})
    make_sweep(sw, "sw_a2", cid, 1, {"1": (0.47, 12.0), "2": (0.5, 3.0)})
    return snap, sw, ex


def _run(world, **kw):
    snap, sw, ex = world
    kw.setdefault("transport", lambda url, params: (200, b'{"markets": []}', {}))
    kw.setdefault("sleep", lambda s: None)
    return cb.extract(snap, sw, ex, **kw)


def test_extracts_only_negrisk_and_postend_with_fields_and_sweep_join(world):
    out = _run(world)
    assert out["extracted"] == 1 and out["missing"] == 0 and out["remaining"] == 0
    ex = world[2]
    neg = pd.read_csv(ex / "negrisk" / "cap_a.csv.gz", dtype=str)
    assert list(neg.columns) == cb.NEGRISK_COLUMNS
    assert sorted(neg["market_id"]) == ["1", "2"]
    n1 = neg[neg.market_id == "1"].iloc[0]
    assert n1.neg_risk_market_id == "NR1" and n1.event_id == "E1" and n1.clob_token_id_0 == "tok1"
    assert float(n1.volume_num) == 1000.0 and n1.fee_category == "politics" and n1.accepting_orders == "1.0"
    assert (float(n1.sw1_best_ask), float(n1.sw1_ask_size_1)) == (0.46, 10.0)
    assert (float(n1.sw2_best_ask), float(n1.sw2_ask_size_1)) == (0.47, 12.0)
    n2 = neg[neg.market_id == "2"].iloc[0]
    assert pd.isna(n2.sw1_best_ask) and float(n2.sw2_best_ask) == 0.5  # not in sweep 1: blank
    post = pd.read_csv(ex / "postend" / "cap_a.csv.gz", dtype=str)
    assert sorted(post["market_id"]) == ["4", "5"]
    p5 = post[post.market_id == "5"].iloc[0]
    assert p5.fav_token == "1" and abs(float(p5.touch) - 0.97) < 1e-9
    p4 = post[post.market_id == "4"].iloc[0]
    assert p4.fav_token == "0" and abs(float(p4.touch) - 0.97) < 1e-9 and p4.fee_schedule
    man = json.loads((ex / "manifest.json").read_text())["captures"]["cap_a"]
    assert man["status"] == "extracted" and man["n_rows"] == 8 and man["n_negrisk"] == 2
    assert man["rows_sha256"] == forecast.sha256_file(world[0] / "cap_a" / "rows.csv.gz")
    assert man["sweeps"] == {"sw1": "sw_a1", "sw2": "sw_a2"}


def test_idempotent_by_capture_id(world):
    _run(world)
    ex = world[2]
    before = {p: p.read_bytes() for p in ex.rglob("*.csv.gz")}
    mtime = (ex / "manifest.json").stat().st_mtime_ns
    out = _run(world)
    assert out["extracted"] == 0 and out["remaining"] == 0
    assert {p: p.read_bytes() for p in ex.rglob("*.csv.gz")} == before
    assert (ex / "manifest.json").stat().st_mtime_ns == mtime
    assert not list(ex.rglob(".tmp_*"))


def test_snapshots_and_sweeps_untouched(world):
    snap, sw, _ = world
    files = [p for r in (snap, sw) for p in r.rglob("*") if p.is_file()]
    before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in files}
    _run(world)
    assert {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in files} == before


def test_missing_rows_file_per_mode(world):
    snap, sw, ex = world
    make_capture(snap, "cap_b", "2026-10-12T02:00:00Z", [_row("cap_b", "1")], [_ext("cap_b", "1")])
    (snap / "cap_b" / "rows.csv.gz").unlink()
    out = _run(world)  # all-new: recorded missing, others still extracted
    assert out["missing"] == 1 and out["extracted"] == 1
    man = json.loads((ex / "manifest.json").read_text())["captures"]
    assert man["cap_b"]["status"] == "missing" and man["cap_a"]["status"] == "extracted"
    with pytest.raises(forecast.ArchivedDataError):
        _run(world, mode="backfill", backfill_from="2026-10-11T12:00:00Z")


def test_script_exit_codes(world, tmp_path):
    snap, sw, ex = world
    make_capture(snap, "cap_b", "2026-10-12T02:00:00Z", [_row("cap_b", "1")])
    (snap / "cap_b" / "rows.csv.gz").unlink()
    base = [sys.executable, str(BACKEND / "scripts" / "run_cb1_extract.py"), "--snapshot-root", str(snap),
            "--sweep-root", str(sw), "--extract-root", str(ex), "--max-requests", "0"]
    r = subprocess.run([*base, "--all-new"], capture_output=True, text=True)
    assert r.returncode == 0 and json.loads(r.stdout.strip().splitlines()[-1])["missing"] == 1
    r = subprocess.run([*base, "--backfill-from", "2026-10-11T12:00Z"], capture_output=True, text=True)
    assert r.returncode == 1 and "ArchivedDataError" in r.stdout


def test_event_members_fetch_cached_and_budgeted(world):
    calls = []

    def tr(url, params):
        calls.append(url)
        return 200, json.dumps({"id": "E1", "markets": [{"closed": False}, {"closed": True},
                                                          {"closed": False}]}).encode(), {}

    _run(world, transport=tr)
    em = pd.read_csv(world[2] / "event_members.csv.gz", dtype=str)
    assert list(em["neg_risk_market_id"]) == ["NR1"] and em.iloc[0].member_count == "3"
    assert em.iloc[0].n_closed == "1" and calls == ["https://gamma-api.polymarket.com/events/E1"]
    _run(world, transport=tr)  # cached: no new request
    assert len(calls) == 1


def test_self_limit_leaves_remaining(world):
    snap, _, ex = world
    for i in range(3):
        make_capture(snap, f"cap_x{i}", f"2026-10-12T0{i + 2}:00:00Z", [_row(f"cap_x{i}", "1")])
    t = {"v": 0.0}

    def clock():
        t["v"] += 100.0  # every call advances: budget 250 s lets ~1 capture through
        return t["v"]

    out = _run(world, clock=clock, budget_s=250.0, max_requests=0)
    assert out["stopped"] == "budget" and out["extracted"] >= 1 and out["remaining"] >= 1
    n_done = out["extracted"]
    out2 = _run(world)  # next run finishes the rest
    assert out2["extracted"] == 4 - n_done and out2["remaining"] == 0


def test_freeze_list_sha_stable_and_extend_only(world):
    snap, sw, ex = world
    _run(world)
    a = cb.freeze_list("dev", ex, snapshot_root=snap, from_utc=None, until="2026-10-13T00:00:00Z",
                       now=lambda: "T1")
    b = cb.freeze_list("dev", ex, snapshot_root=snap, from_utc=None, until="2026-10-13T00:00:00Z",
                       now=lambda: "T2")
    assert a["sha256"] == b["sha256"] and b["created_utc"] == "T1"  # unchanged: not rewritten
    assert a["capture_ids"] == ["cap_a"] and not a["final"] and a["missing_ids"] == []
    assert cb.load_capture_list(ex, "dev")["sha256"] == cb.ids_sha256(["cap_a"])
    make_capture(snap, "cap_c", "2026-10-12T12:00:00Z", [_row("cap_c", "1")])
    c = cb.freeze_list("dev", ex, snapshot_root=snap, from_utc=None, until="2026-10-17T00:00:00Z")
    assert c["capture_ids"] == ["cap_a", "cap_c"] and c["final"] and c["previous_sha256"] == a["sha256"]
    assert c["missing_ids"] == ["cap_c"]  # in the list, not yet extracted: counted
    with pytest.raises(ValueError):
        cb.freeze_list("dev", ex, snapshot_root=snap, from_utc="2026-10-12T06:00:00Z",
                       until="2026-10-17T00:00:00Z")
    p = ex / "capture_lists" / "dev.json"
    d = json.loads(p.read_text())
    d["capture_ids"].append("zzz")
    p.write_text(json.dumps(d))
    with pytest.raises(ValueError, match="sha256"):
        cb.load_capture_list(ex, "dev")


def test_backfill_complete_writes_dev_list(world):
    out = _run(world, mode="backfill", backfill_from="2026-10-11T12:00:00Z", write_dev_list=True,
               now=lambda: "2026-10-14T00:00:00Z")
    assert out["backfill_complete"] is True and out["dev_list"]
    assert cb.load_capture_list(world[2], "dev")["capture_ids"] == ["cap_a"]


def test_lock_blocks_concurrent_run(world):
    ex = world[2]
    with cb._lock(ex), pytest.raises(cb.ExtractLocked):
        _run(world)


# --- memory bound on a synthetic ~300k-row capture ---------------------------------------------------

_MEM_SCRIPT = r"""
import json, resource, sys, time
from pathlib import Path
from astrolabe.research_lab import creative_batch1 as cb
snap, sw, ex = map(Path, sys.argv[1:4])
t = time.time()
out = cb.extract(snap, sw, ex, max_requests=0)
rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
rss_mb = rss / 1e6 if sys.platform == "darwin" else rss / 1e3
print(json.dumps({"rss_mb": rss_mb, "s": time.time() - t, "out": out}))
"""


def test_peak_rss_on_300k_row_capture(tmp_path):
    n = 300_000
    rng = np.random.default_rng(0)
    bid = np.round(rng.uniform(0.01, 0.97, n), 3)
    ids = np.arange(n).astype(str)
    nr = np.where(rng.random(n) < 0.05, "NR" + (np.arange(n) % 900).astype(str), "")
    df = pd.DataFrame({
        "capture_id": "big", "capture_start_utc": "2026-10-12T00:00:00Z",
        "received_utc": "2026-10-12T00:05:00.123456Z", "market_id": ids,
        "condition_id": "0x" + pd.Series(ids).str.zfill(64), "event_id": (np.arange(n) // 3).astype(str),
        "closed": "False", "active": "True", "binary": 1, "best_bid": bid, "best_ask": bid + 0.02,
        "spread": 0.02, "last_trade_price": bid, "chg_1h": 0.001, "chg_1d": 0.002, "chg_1w": 0.003,
        "liquidity": 1234.5, "volume24hr": 99.9, "end_date": "2026-12-01T00:00:00Z",
        "updated_at": "2026-10-12T00:04:00.000Z", "dup_count": 0,
        "clob_token_id_0": "7" * 70 + pd.Series(ids), "neg_risk": (nr != "").astype(int),
        "neg_risk_market_id": nr, "neg_risk_other": 0, "event_neg_risk_augmented": 0, "page_index": 1})
    snap = tmp_path / "snap"
    d = snap / "big"
    d.mkdir(parents=True)
    _write_gz(d / "rows.csv.gz", df)
    ext = pd.DataFrame({"capture_id": "big", "market_id": ids, "accepting_orders": 1, "fees_enabled": 1,
                        "volume_num": 5000.0, "fee_schedule": '{"rate":0.04,"exponent":1}',
                        "fee_category": "politics"})
    _write_gz(d / "rows_ext.csv.gz", ext)
    (d / "ext_manifest.json").write_text("{}")
    (d / "manifest.json").write_text(json.dumps({"capture_id": "big",
                                                  "started_utc": "2026-10-12T00:00:00Z",
                                                  "state": "complete"}))
    del df, ext
    env = {**os.environ, "PYTHONPATH": str(BACKEND)}
    t = time.time()
    r = subprocess.run([sys.executable, "-c", _MEM_SCRIPT, str(snap), str(tmp_path / "sw"),
                        str(tmp_path / "ex")], capture_output=True, text=True, env=env, cwd=BACKEND)
    assert r.returncode == 0, r.stderr[-800:]
    res = json.loads(r.stdout.strip().splitlines()[-1])
    print(f"\nCB1 extract synthetic 300k rows: peak RSS {res['rss_mb']:.0f} MB, "
          f"{res['s']:.1f} s in-process, {time.time() - t:.1f} s wall")
    assert res["out"]["extracted"] == 1
    assert res["rss_mb"] < 500
    neg = pd.read_csv(tmp_path / "ex" / "negrisk" / "big.csv.gz", dtype=str)
    assert len(neg) == int((nr != "").sum()) > 10_000
