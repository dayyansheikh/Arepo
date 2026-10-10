"""Trade sample tests with fake transports only (no network)."""

from __future__ import annotations

import gzip
import json
from datetime import UTC, datetime, timedelta
from fractions import Fraction
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import trade_sample as ts
from astrolabe.research_lab.extract import COLUMNS

ORIGIN = "2026-10-10T20:00:00.000000Z"
ORIGIN_EPOCH = datetime(2026, 10, 10, 20, tzinfo=UTC).timestamp()
SENT0 = datetime(2026, 10, 10, 23, tzinfo=UTC)
SEED = "ab" * 16


def make_rows(n=120, flat=False):
    rng = np.random.default_rng(1)
    recs = []
    for i in range(n):
        bid = 0.40 + 0.001 * (i % 7)
        recs.append({
            "capture_id": "cap", "capture_start_utc": ORIGIN, "received_utc": ORIGIN,
            "market_id": str(1000 + i), "condition_id": f"0xc{i:04d}", "event_id": "e",
            "closed": False, "active": True, "binary": 1, "best_bid": bid,
            "best_ask": bid + 0.005 * (1 + i % 5), "spread": 0.005 * (1 + i % 5),
            "liquidity": float(rng.uniform(100, 10000)), "end_date": "2027-01-01T00:00:00Z",
            "clob_token_id_0": f"tok{i}",
        })
    recs.append({**recs[0], "market_id": "9999", "closed": True})  # ineligible
    recs.append({**recs[1], "market_id": "9998", "binary": 0})  # ineligible
    df = pd.DataFrame(recs)
    if flat:  # one stratum: constant liquidity and spread
        df["liquidity"], df["spread"] = 1000.0, 0.01
        df["best_ask"] = df["best_bid"] + 0.01
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = np.nan
    return df


def make_snapshot(tmp_path: Path, rows=None) -> Path:
    d = tmp_path / "snap"
    d.mkdir(exist_ok=True)
    rows = make_rows(flat=True) if rows is None else rows
    rows.to_csv(d / "rows.csv.gz", index=False)
    (d / "manifest.json").write_text(json.dumps({"capture_id": "cap", "state": "complete"}))
    return d


def trade(t, side="BUY", size=10.0, price=0.5, oi=0, asset="tok0"):
    return {"timestamp": t, "side": side, "size": size, "price": price, "outcomeIndex": oi,
            "asset": asset, "transactionHash": f"0x{t}", "proxyWallet": "0xwallet"}


class Fake:
    def __init__(self, per_market=None, script=None, hook=None):
        self.calls: list[dict] = []
        self.per_market = per_market or {}
        self.script = script or []
        self.hook = hook

    def __call__(self, params):
        self.calls.append(params)
        if self.hook:
            self.hook()
        if self.script:
            code = self.script.pop(0)
            if isinstance(code, Exception):
                raise code
            if code != 200:
                return code, b"", {}
        body = self.per_market.get(params["market"], [])
        return 200, json.dumps(body).encode(), {}


class Clock:
    def __init__(self):
        self.t = SENT0

    def __call__(self):
        self.t += timedelta(milliseconds=5)
        return self.t


def run(tmp_path, transport, **kw):
    snap = make_snapshot(tmp_path)
    return ts.run(snap, transport, out_root=tmp_path / "out", sleep=lambda s: None,
                  now=Clock(), seed=SEED, **kw), tmp_path / "out"


def test_stratification_allocation_and_probabilities():
    frame = ts.build_frame(make_rows())
    assert len(frame) == 120  # ineligible rows excluded
    strata, cuts = ts.assign_strata(frame)
    assert len(cuts["liquidity_quartile_cuts"]) == 3 and len(cuts["spread_tercile_cuts"]) == 2
    sample = ts.draw_sample(frame, strata, 40, SEED)
    assert len(sample) == 40 and sample["condition_id"].is_unique
    sizes = strata.value_counts().to_dict()
    assert all(v >= 1 for v in sample["stratum"].value_counts())
    assert sample["stratum"].nunique() == len(sizes)
    # sum over frame of inclusion probability == sample size
    tot = sum(Fraction(int(g["n_h"].iloc[0]), int(g["N_h"].iloc[0])) * int(g["N_h"].iloc[0])
              for _, g in sample.groupby("stratum"))
    assert tot == 40


def test_allocate_min_one_and_cap():
    a = ts.allocate({"a": 1000, "b": 3, "c": 1}, 20)
    assert sum(a.values()) == 20 and a["b"] >= 1 and a["c"] == 1
    assert ts.allocate({"a": 5, "b": 2}, 100) == {"a": 5, "b": 2}
    with pytest.raises(ValueError):
        ts.allocate({"a": 5, "b": 5}, 1)


def test_determinism_given_seed_and_difference_across_seeds():
    frame = ts.build_frame(make_rows())
    strata, _ = ts.assign_strata(frame)
    a = ts.draw_sample(frame, strata, 30, SEED)
    b = ts.draw_sample(frame, strata, 30, SEED)
    c = ts.draw_sample(frame, strata, 30, "cd" * 16)
    assert a["condition_id"].tolist() == b["condition_id"].tolist()
    assert a["condition_id"].tolist() != c["condition_id"].tolist()


def test_seed_sealed_before_first_request(tmp_path):
    seen = {}
    out_dir = tmp_path / "out"

    def hook():
        if "plan" in seen:
            return
        d = next(out_dir.iterdir())
        plan = json.loads((d / "plan.json").read_text())
        man = json.loads((d / "manifest.json").read_text())
        seen["plan"] = plan["seed"]
        seen["state"] = man["state"]
        seen["man_seed"] = man["seed"]
        seen["trades_exist"] = (d / "trades.csv.gz").exists()

    fake = Fake(hook=hook)
    man, _ = run(tmp_path, fake, n_total=10)
    assert seen == {"plan": SEED, "state": "planned", "man_seed": SEED, "trades_exist": False}
    assert man["state"] == "complete" and man["request_count"] == 10
    assert all(c["limit"] == 500 for c in fake.calls)


def test_sum_inclusion_over_frame_in_plan(tmp_path):
    rows = make_rows()
    plan, _ = ts.build_plan(rows, {"capture_id": "c"}, "", "", 40, SEED)
    assert plan["sum_inclusion_over_frame"] == pytest.approx(40)
    assert plan["n_sampled"] == 40 and plan["frame_size"] == 120
    assert {m["inclusion_prob"] for m in plan["sample"]} <= {s["inclusion_prob"]
                                                             for s in plan["strata"]}


def test_default_seed_is_random_hex(tmp_path):
    snap = make_snapshot(tmp_path)
    m = ts.run(snap, Fake(), n_total=5, out_root=tmp_path / "o", sleep=lambda s: None,
               now=Clock())
    assert len(m["seed"]) == 32 and int(m["seed"], 16) >= 0


def test_features_use_only_trades_before_origin():
    trades, _ = ts.parse_trades(json.dumps([
        trade(ORIGIN_EPOCH + 10, size=1000),  # after origin: excluded
        trade(ORIGIN_EPOCH, size=500),  # at origin: not strictly before
        trade(ORIGIN_EPOCH - 60, "BUY", 4, 0.5, 0),
        trade(ORIGIN_EPOCH - 120, "SELL", 1, 0.5, 0),
        trade(ORIGIN_EPOCH - 180, "BUY", 2, 0.5, 1, "tok1"),  # buy outcome 1 -> negative
        trade(ORIGIN_EPOCH - 200, "SELL", 3, 0.5, 1, "tok1"),  # sell outcome 1 -> positive
        trade(ORIGIN_EPOCH - 4000, "BUY", 99),  # outside 1h window
    ]).encode())
    f = ts.origin_features(trades, ORIGIN_EPOCH, len(trades), "tok0")
    assert f["n_trades_1h"] == 4
    assert f["volume_1h"] == 10
    assert f["signed_volume_1h"] == 4 - 1 - 2 + 3
    assert f["max_trade_size_1h"] == 4
    assert f["time_since_last_trade_s"] == 60
    assert f["trades_truncated"] is False


def test_sign_falls_back_to_asset_and_counts_unsigned():
    t = [{"ts": int(ORIGIN_EPOCH) - 5, "side": "BUY", "price": .5, "size": 2.0,
          "outcome_index": None, "asset": "tok0", "tx_hash": "a"},
         {"ts": int(ORIGIN_EPOCH) - 6, "side": "BUY", "price": .5, "size": 7.0,
          "outcome_index": None, "asset": "other", "tx_hash": "b"}]
    f = ts.origin_features(t, ORIGIN_EPOCH, 2, "tok0")
    assert f["signed_volume_1h"] == 2 and f["n_unsigned"] == 1


def test_no_prior_trades_gives_nan_and_zero():
    f = ts.origin_features([], ORIGIN_EPOCH, 0, "tok0")
    assert f["n_trades_1h"] == 0 and np.isnan(f["time_since_last_trade_s"])
    assert f["trades_truncated"] is False


def test_truncation_flag():
    full = [{"ts": int(ORIGIN_EPOCH) - 10 - i, "side": "BUY", "price": .5, "size": 1.0,
             "outcome_index": 0, "asset": "t", "tx_hash": str(i)} for i in range(500)]
    assert ts.origin_features(full, ORIGIN_EPOCH, 500, "t")["trades_truncated"] is True
    # oldest returned trade older than the window start: window fully covered
    full[-1]["ts"] = int(ORIGIN_EPOCH) - 7200
    assert ts.origin_features(full, ORIGIN_EPOCH, 500, "t")["trades_truncated"] is False
    # fewer than the limit returned: never truncated
    assert ts.origin_features(full[:100], ORIGIN_EPOCH, 100, "t")["trades_truncated"] is False


def test_future_trades_dropped_and_counted(tmp_path):
    snap = make_snapshot(tmp_path)
    plan, _ = ts.build_plan(pd.read_csv(snap / "rows.csv.gz", dtype={"market_id": str}),
                            {"capture_id": "cap"}, "", "", 3, SEED)
    cid = plan["sample"][0]["condition_id"]
    sent_epoch = SENT0.timestamp()
    body = [trade(int(sent_epoch) + 3600), trade(int(sent_epoch) - 100),
            trade(int(ORIGIN_EPOCH) - 30)]
    man, out = run(tmp_path, Fake({cid: body}), n_total=3)
    d = next(out.iterdir())
    trades = pd.read_csv(d / "trades.csv.gz")
    assert len(trades) == 2 and (trades["ts"] <= sent_epoch + 1).all()
    assert man["dropped_future_trades"] == 1
    feats = pd.read_csv(d / "features.csv.gz")
    row = feats[feats["condition_id"] == cid].iloc[0]
    assert row["n_dropped_future"] == 1 and row["n_trades_1h"] == 1


def test_retry_then_success_and_exhaustion(tmp_path):
    fake = Fake(script=[429, 503, 200])
    man, _ = run(tmp_path, fake, n_total=1)
    assert man["request_count"] == 3 and man["retry_count"] == 2
    assert man["status_counts"] == {"ok": 1}
    assert [r["attempt"] for r in man["requests"]] == [0, 1, 2]
    assert all(len(r["sha256"]) == 64 for r in man["requests"])


def test_retries_exhausted_max_five(tmp_path):
    fake = Fake(script=[500] * 6 + [200] * 5)
    man, _ = run(tmp_path, fake, n_total=2)
    assert man["status_counts"] == {"retries_exhausted": 1, "ok": 1}
    assert man["request_count"] == 6 + 1  # 1 try + 5 retries, then next market ok


def test_network_exception_is_retried(tmp_path):
    fake = Fake(script=[ConnectionError("x"), 200])
    man, _ = run(tmp_path, fake, n_total=1)
    assert man["status_counts"] == {"ok": 1} and man["requests"][0]["status"] == "ConnectionError"


def test_request_cap_marks_incomplete(tmp_path):
    man, out = run(tmp_path, Fake(), n_total=10, max_requests=4)
    assert man["state"] == "incomplete" and man["stop_reason"] == "request_cap"
    assert man["request_count"] == 4
    assert man["status_counts"] == {"ok": 4, "not_attempted": 6}


def test_time_cap(tmp_path):
    ticks = iter([0.0, 0.0, 0.0, 5000.0] + [5000.0] * 50)
    man, _ = run(tmp_path, Fake(), n_total=5, clock=lambda: next(ticks), max_seconds=1200)
    assert man["state"] == "incomplete" and man["stop_reason"] == "time_cap"


def test_atomic_outputs_leave_no_tmp_and_manifest_final(tmp_path):
    man, out = run(tmp_path, Fake(), n_total=5, keep_raw=True)
    d = next(out.iterdir())
    assert not list(d.glob("*.tmp")) and not list(d.rglob("*.tmp"))
    assert {p.name for p in d.iterdir()} == {"plan.json", "trades.csv.gz", "features.csv.gz",
                                             "manifest.json", "raw"}
    assert len(list((d / "raw").iterdir())) == 5
    assert json.loads((d / "manifest.json").read_text())["state"] == "complete"
    with gzip.open(d / "features.csv.gz", "rt") as fh:
        assert fh.readline().strip().split(",") == ts.FEATURE_COLS


def test_atomic_write_replaces_without_partial(tmp_path):
    p = tmp_path / "x.json"
    ts.atomic_write(p, b"one")
    ts.atomic_write(p, b"two")
    assert p.read_bytes() == b"two" and not (tmp_path / "x.json.tmp").exists()


def test_non_json_body_is_schema_error(tmp_path):
    class Bad(Fake):
        def __call__(self, params):
            return 200, b"<html>", {}

    man, _ = run(tmp_path, Bad(), n_total=2)
    assert man["status_counts"] == {"schema_error": 2}
