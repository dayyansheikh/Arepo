# ruff: noqa: E501
"""CB3 post-window follow-up step (docs/research_lab/CREATIVE_BATCH_3.md §4.3.2)."""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

import pandas as pd

from astrolabe.research_lab import cb3_followup as F
from astrolabe.research_lab import cb3_maker as M

ADDR = "0x" + "ab12" * 10


def _gz(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", newline="") as fh:
        df.to_csv(fh, index=False)


def world(tmp_path: Path, n_markets: int = 40):
    snaps = tmp_path / "snapshots"
    for cid, st in (("cap0", "2026-10-20T00:00:00Z"), ("cap1", "2026-10-20T02:00:00Z")):
        d = snaps / cid
        d.mkdir(parents=True)
        (d / "manifest.json").write_text(json.dumps({"capture_id": cid, "started_utc": st, "state": "complete"}))
    samp = tmp_path / "trade_samples" / "S1"
    samp.mkdir(parents=True)
    plan = {"sample": [{"market_id": f"m{i}", "condition_id": f"c{i}", "stratum": "s", "origin_utc": "2026-10-20T00:05:00Z", "token0": "t0"} for i in range(n_markets)]}
    (samp / "plan.json").write_text(json.dumps(plan))
    (samp / "manifest.json").write_text(json.dumps({"snapshot_id": "cap0", "state": "complete"}))
    tr = pd.DataFrame([{"market_id": f"m{i}", "condition_id": f"c{i}", "ts": 1_760_000_000 + i, "side": "BUY", "price": 0.5, "size": 3.0, "outcome_index": 0, "asset": "t0", "tx_hash": f"0xt{i}"} for i in range(n_markets)])
    wl = pd.DataFrame([{"market_id": f"m{i}", "condition_id": f"c{i}", "ts": 1_760_000_000 + i, "side": "BUY", "outcome_index": 0, "asset": "t0", "size": 3.0, "price": 0.5, "wallet_hash": f"h{i}"} for i in range(n_markets)])
    _gz(samp / "trades.csv.gz", tr)
    _gz(samp / "wallets.csv.gz", wl)
    return snaps, tmp_path / "trade_samples", samp


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.t += s


def page(n, t0=1_760_100_000):
    return json.dumps([{"timestamp": t0 + i, "side": "BUY", "price": 0.5, "size": 1.0, "outcomeIndex": 0, "asset": "t0", "transactionHash": f"0x{i}", "proxyWallet": ADDR}
                       for i in range(n)]).encode()


def digest(root: Path) -> dict:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob("*")) if p.is_file()}


def run(tmp_path, transport, **kw):
    snaps, samp_root, _ = world(tmp_path)
    clk = Clock()
    args = dict(snapshot_root=snaps, sample_root=samp_root, qs_root=tmp_path / "none", out_root=tmp_path / "fu", transport=transport, key=b"k" * 32,
                sleep=clk.sleep, clock=clk, now=lambda: 1_760_100_500.0, seed="seed1")
    args.update(kw)
    return F.run(**args), snaps, samp_root


def test_seed_sealed_before_first_request_and_pre_rows_copied_unchanged(tmp_path):
    seen = {}

    def tr(params):
        plan = tmp_path / "fu" / "cap1" / "plan.json"
        seen.setdefault("plan_at_first_request", plan.exists())
        seen["seed"] = json.loads(plan.read_text())["seed"] if plan.exists() else None
        return 200, page(3), {}

    res, _s, samp_root = run(tmp_path, tr)
    assert seen["plan_at_first_request"] is True and seen["seed"] == "seed1"
    pre = pd.read_csv(tmp_path / "fu" / "cap1" / "pre" / "trades.csv.gz", dtype=str, keep_default_na=False)
    src = pd.read_csv(samp_root / "S1" / "trades.csv.gz", dtype=str, keep_default_na=False)
    assert pre.equals(src[src["market_id"].isin(pre["market_id"])].reset_index(drop=True)) and 0 < len(pre) < len(src)
    assert res["n_sample_markets"] == len(pre)


def test_fifty_percent_draw_is_reproducible():
    ids = [f"m{i}" for i in range(400)]
    a, b = F.seeded_subsample(ids, "s", 0.5), F.seeded_subsample(ids, "s", 0.5)
    assert a == b and 150 < len(a) < 250
    assert F.seeded_subsample(ids, "other", 0.5) != a


def test_windowed_paging_covers_window_or_flags_the_page_cap(tmp_path):
    calls = []

    def tr(params):
        calls.append(params)
        assert params["takerOnly"] == "true" and params["limit"] == 1000 and "start" in params and "end" in params
        n = 1000 if params["offset"] < 2000 else 300
        return 200, page(n, 1_760_100_000 - params["offset"]), {}

    clk = Clock()
    bud = F.Budget(4.0, 540.0, clk)
    w = F.window_trades(tr, "c1", 1_760_000_000, 1_760_100_500, sleep=clk.sleep, budget=bud, key=b"k")
    assert w["pages"] == 3 and w["page_cap"] is False and len(w["rows"]) == 2300
    assert [c["offset"] for c in calls] == [0, 1000, 2000]

    def full(params):
        return 200, page(1000, 1_760_100_000 - params["offset"]), {}

    w2 = F.window_trades(full, "c1", 1_760_000_000, 1_760_100_500, sleep=clk.sleep, budget=F.Budget(4.0, 540.0, clk), key=b"k")
    assert w2["pages"] == 5 and w2["page_cap"] is True and w2["oldest_ts"] is not None


def test_no_raw_wallet_in_any_file_and_trade_sample_directory_is_byte_identical(tmp_path):
    snaps, samp_root, _ = world(tmp_path)
    before = digest(samp_root)
    clk = Clock()
    F.run(snapshot_root=snaps, sample_root=samp_root, qs_root=tmp_path / "none", out_root=tmp_path / "fu", transport=lambda p: (200, page(5), {}), key=b"k" * 32,
          sleep=clk.sleep, clock=clk, now=lambda: 1_760_100_500.0, seed="x")
    assert digest(samp_root) == before
    assert F.has_raw_address(tmp_path / "fu") is False
    post = pd.read_csv(tmp_path / "fu" / "cap1" / "post" / "trades.csv.gz")
    assert post["wallet_hash"].notna().all() and ADDR not in post.to_csv()


def test_budget_ends_the_step_and_unreached_markets_are_counted_in_seeded_order(tmp_path):
    order = []

    def tr(params):
        order.append(params["market"])
        return 200, page(2), {}

    res, _s, _r = run(tmp_path, tr, budget_s=3.0, rps=1.0)
    plan = json.loads((tmp_path / "fu" / "cap1" / "plan.json").read_text())
    planned = [m for _k, m in plan["request_order"]]
    assert res["stopped"] == "budget" and res["not_reached"] > 0
    assert [f"c{m[1:]}" for m in planned[: len(order)]] == order  # requested in the sealed seeded order
    assert res["requests"] <= 4  # 1 rps, 3 s budget


def test_429_stop_after_fifty_and_retry_after_is_honoured(tmp_path):
    waits = []
    snaps, samp_root, _ = world(tmp_path)
    clk = Clock()

    def sl(s):
        waits.append(s)
        clk.sleep(s)

    res = F.run(snapshot_root=snaps, sample_root=samp_root, qs_root=tmp_path / "none", out_root=tmp_path / "fu", transport=lambda p: (429, b"", {"Retry-After": "7"}),
                key=b"k" * 32, sleep=sl, clock=clk, now=lambda: 1_760_100_500.0, seed="x", budget_s=1e9)
    assert res["stopped"] == "429_stop" and res["n_429"] >= 50
    assert 7.0 in waits


def test_refuses_when_data_dumps_is_over_the_cap(tmp_path):
    snaps, samp_root, _ = world(tmp_path)
    res = F.run(snapshot_root=snaps, sample_root=samp_root, qs_root=tmp_path / "none", out_root=tmp_path / "fu", transport=lambda p: (200, page(1), {}),
                data_dumps=tmp_path, data_dumps_max_gb=0.0, dir_gb=lambda p: 12.0, seed="x")
    assert res["stopped"] == "refused_data_dumps_over_cap" and not (tmp_path / "fu").exists()


def test_idempotent_per_capture(tmp_path):
    res, snaps, samp_root = run(tmp_path, lambda p: (200, page(1), {}))
    again = F.run(snapshot_root=snaps, sample_root=samp_root, qs_root=tmp_path / "none", out_root=tmp_path / "fu", transport=lambda p: (200, page(1), {}), seed="y")
    assert again["stopped"] == "already_done"


def test_reader_roundtrip_pre_uses_hashed_wallets_and_union_dedupes(tmp_path):
    run(tmp_path, lambda p: (200, page(3), {}))
    rd = M.FollowupReader(tmp_path / "fu")
    pre = rd.trades("cap1", "pre", "m0") if (tmp_path / "fu" / "cap1" / "pre" / "wallets.csv.gz").exists() else None
    post = rd.trades("cap1", "post", "m0")
    assert len(post["ts"]) in (0, 3) and (pre is None or pre["wallet"].dtype == object)
    t = float(post["ts"][0]) - 1 if len(post["ts"]) else 0.0
    u = M.prints_union(post, post, t)  # the same print in both sources counts once
    assert len(u["ts"]) == len(post["ts"])
