"""E007 tests on synthetic samples and snapshots (no data-dumps access)."""

from __future__ import annotations

import gzip
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import e007, forecast

REG = datetime(2026, 10, 11, 10, 0, 0, tzinfo=UTC)
FMT = "%Y-%m-%dT%H:%M:%S.%fZ"
N = 60


def _h(hours: float) -> datetime:
    return REG + timedelta(hours=hours)


def _write_snap(root: Path, cap: str, start: datetime, state: str = "complete") -> None:
    d = root / cap
    d.mkdir(parents=True)
    (d / "manifest.json").write_text(json.dumps(
        {"capture_id": cap, "state": state, "started_utc": start.strftime("%Y-%m-%dT%H:%M:%SZ")}))
    chg = np.linspace(-0.02, 0.02, N)
    mids = np.full(N, 0.5) if cap != "t" else 0.5 + 0.1 * chg
    pd.DataFrame({
        "capture_id": cap, "capture_start_utc": start.isoformat(),
        "received_utc": (start + timedelta(seconds=30)).strftime(FMT),
        "market_id": [str(i) for i in range(N)], "condition_id": [f"0x{i}" for i in range(N)],
        "event_id": [str(i // 2) for i in range(N)], "closed": False, "active": True,
        "binary": 1, "best_bid": mids - 0.01, "best_ask": mids + 0.01, "spread": 0.02,
        "last_trade_price": mids, "chg_1h": chg, "chg_1d": 0.0, "chg_1w": 0.0,
        "liquidity": 1000.0, "volume24hr": 50.0, "end_date": "2027-01-01T00:00:00Z",
    }).to_csv(d / "rows.csv.gz", index=False)


def _write_sample(root: Path, sid: str, src: str, src_start: datetime, sealed: datetime, *,
                  ids=None, frame="active", state="complete", sent_offset_s=60.0) -> None:
    d = root / sid
    d.mkdir(parents=True)
    ids = [str(i) for i in range(N)] if ids is None else [str(i) for i in ids]
    man = {"sample_id": sid, "state": state, "snapshot_id": src, "frame": frame,
           "started_utc": sealed.strftime(FMT),
           "finished_utc": (sealed + timedelta(minutes=5)).strftime(FMT)}
    (d / "manifest.json").write_text(json.dumps(man))
    (d / "plan.json").write_text(json.dumps(
        {"sample": [{"market_id": m, "inclusion_float": 0.5} for m in ids]}))
    vol = np.arange(len(ids), dtype=float) % 5 + 1
    pd.DataFrame({
        "market_id": ids, "origin_utc": (src_start + timedelta(seconds=30)).strftime(FMT),
        "sent_utc": (sealed + timedelta(seconds=sent_offset_s)).strftime(FMT), "status": "ok",
        "n_trades_1h": 3, "volume_1h": vol, "signed_volume_1h": vol * 0.5,
        "max_trade_size_1h": vol / 2, "time_since_last_trade_s": 100.0,
        "trades_truncated": False,
    }).to_csv(d / "features.csv.gz", index=False)
    with gzip.open(d / "trades.csv.gz", "wt") as fh:
        fh.write("market_id\n")


@pytest.fixture
def roots(tmp_path):
    return tmp_path / "samples", tmp_path / "snaps"


def _caps(snaps: Path, specs):
    for cid, start in specs:
        _write_snap(snaps, cid, start)
    return forecast.list_complete_captures(snaps)


def test_qualification_rules(roots):
    samples, snaps = roots
    caps = _caps(snaps, [("a", _h(1)), ("b", _h(3)), ("c", _h(4)), ("d", _h(6)), ("e", _h(9))])

    def ok(sid, src, hrs, **k):
        _write_sample(samples, sid, src, _h(hrs), _h(hrs + 0.1), **k)

    ok("pre", "a", 1)
    samples_pre = samples / "pre"
    m = json.loads((samples_pre / "manifest.json").read_text())
    m["started_utc"] = _h(-1).strftime(FMT)  # sealed before registration
    (samples_pre / "manifest.json").write_text(json.dumps(m))
    ok("good", "b", 3)
    ok("dup1", "c", 4)
    ok("dup2", "c", 4, sent_offset_s=900.0)
    ok("late", "d", 6)  # d -> e is exactly 3h: allowed
    ok("slow", "e", 9, sent_offset_s=1.0)  # no later snapshot -> unavailable
    metas = e007.list_metas(samples)
    cands, excl = e007.classify(metas, caps, REG)
    assert [c["sample_id"] for c in cands] == ["good", "dup1", "late"]
    assert excl["seed_sealed_before_registration"] == ["pre"]
    assert excl["duplicate_source_snapshot"] == ["dup2"]
    assert excl["unavailable_no_target_snapshot"] == ["slow"]


def test_gap_over_3h_and_requests_after_target_start(roots):
    samples, snaps = roots
    caps = _caps(snaps, [("a", _h(1)), ("b", _h(4.5)), ("c", _h(5)), ("d", _h(6))])
    _write_sample(samples, "gap", "a", _h(1), _h(1.1))
    _write_sample(samples, "slow", "c", _h(5), _h(5.1), sent_offset_s=3700.0)
    cands, excl = e007.classify(e007.list_metas(samples), caps, REG)
    assert cands == []
    assert excl["target_gap_over_3h"] == ["gap"]
    assert excl["requests_not_before_target_start"] == ["slow"]


def test_source_with_pre_registration_sample_excluded(roots):
    samples, snaps = roots
    caps = _caps(snaps, [("a", _h(-1)), ("b", _h(1))])
    _write_sample(samples, "dev", "a", _h(-1), _h(-0.9))
    _write_sample(samples, "conf", "a", _h(-1), _h(1.2))
    _write_sample(samples, "eligible", "b", _h(1), _h(1.1), frame="eligible")
    cands, excl = e007.classify(e007.list_metas(samples), caps, REG)
    assert cands == []
    assert excl["source_has_pre_registration_sample"] == ["conf"]
    assert excl["not_active_frame"] == ["eligible"]


def test_fewer_than_150_nonzero_excluded_and_counted(roots):
    samples, snaps = roots
    _caps(snaps, [("a", _h(1)), ("b", _h(3))])
    _write_sample(samples, "s", "a", _h(1), _h(1.1))
    qual, pairs, excl = e007.build_confirmation(samples, snaps, REG)  # default min 150
    assert qual == [] and pairs.empty
    assert excl["fewer_than_150_nonzero_pairs"] == ["s"]
    qual, pairs, _ = e007.build_confirmation(samples, snaps, REG, min_nonzero=20)
    assert len(qual) == 1 and qual[0]["nonzero"] == N and len(pairs) == N
    st = e007.status(samples, snaps, snaps / "out", REG, REG + timedelta(days=1), 20)
    assert st["qualifying"] == 1 and not st["ready"] and not st["past_deadline"]


def test_dev_merge_of_duplicate_source_sample(roots, monkeypatch):
    samples, snaps = roots
    _caps(snaps, [("c1", _h(-6)), ("t", _h(-4))])
    _write_sample(samples, "first", "c1", _h(-6), _h(-5.9), ids=range(0, 40))
    _write_sample(samples, "later", "c1", _h(-6), _h(-3.5), ids=range(20, 60))
    _write_sample(samples, "justbefore", "c1", _h(-6), _h(-0.01), ids=range(0, 10),
                  state="planned")
    _write_sample(samples, "elig", "c1", _h(-6), _h(-5), frame="eligible")
    monkeypatch.setattr(e007, "DEV_SOURCES", ("c1",))
    out = snaps / "e007"
    fit = e007.fit_dev(samples, snaps, out, REG)
    assert fit["n_total"] == 60  # 40 + 20 markets not in the first sample
    assert fit["merged_duplicates"]["later"]["markets_not_in_first_sample"] == 20
    reasons = {x["sample_id"]: x["reason"] for x in fit["excluded_dev_samples"]}
    assert reasons == {"justbefore": "excluded_dev_sample",
                       "elig": "eligible frame (not trade-active)"}
    assert fit["per_period"]["1"]["nonzero_signed_share"] == 60
    assert fit["provenance"]["code_sha256"] and "first" in fit["input_manifest_sha256"][
        "trade_samples"]
    with pytest.raises(FileExistsError):
        e007.fit_dev(samples, snaps, out, REG)
    assert "n=60" in e007.ledger_line(fit, "abc")


def _synthetic(beta_by_period, n=300, seed=3, noise=0.002):
    rng = np.random.default_rng(seed)
    rows = []
    for p, b in enumerate(beta_by_period):
        chg = rng.normal(0, 0.02, n)
        ss = rng.uniform(-1, 1, n) * (rng.random(n) < 0.6)
        rows.append(pd.DataFrame({
            "period": p, "market_id": [f"{p}_{i}" for i in range(n)],
            "event_id": [f"{p}_{i // 2}" for i in range(n)], "chg_1h": chg,
            "signed_share": ss, "dmid": -0.1 * chg + b * ss + rng.normal(0, noise, n),
            "w": 2.0}))
    return pd.concat(rows, ignore_index=True)


FIT = {"base": {"intercept": 0.0, "chg_1h": -0.1},
       "augmented": {"intercept": 0.0, "chg_1h": -0.1, "signed_share": 0.01}}


def test_primary_supported_and_consistency():
    res = e007.analyse(_synthetic([0.01] * 12), FIT, n_boot=200)
    assert res["primary"]["beta"] == pytest.approx(0.01, abs=2e-3)
    assert res["primary"]["rejects_zero"] and res["consistency"]["n_positive"] == 12
    assert res["verdict"].startswith("Supported")
    assert res["secondary_descriptive"]["delta_r2"] > 0
    assert res["category"]["status"] == "unavailable"


def test_consistency_failure_gives_inconclusive():
    betas = [0.05] * 7 + [-0.002] * 5
    res = e007.analyse(_synthetic(betas), FIT, n_boot=200)
    assert res["primary"]["rejects_zero"] and res["primary"]["beta"] > 0
    assert res["consistency"]["n_positive"] == 7 and not res["consistency"]["met"]
    assert res["verdict"] == "Inconclusive"


def test_contradicted_and_null():
    neg = e007.analyse(_synthetic([-0.01] * 12), FIT, n_boot=200)
    assert neg["verdict"] == "Contradicted"
    null = e007.analyse(_synthetic([0.0] * 12, noise=0.05), FIT, n_boot=200)
    assert null["verdict"] == "Inconclusive"


def test_unavailable_after_deadline_and_refuse_overwrite(roots):
    samples, snaps = roots
    _caps(snaps, [("a", _h(1)), ("b", _h(3))])
    _write_sample(samples, "s", "a", _h(1), _h(1.1))
    out = snaps / "e007"
    out.mkdir()
    (out / "dev_fit.json").write_text(json.dumps(FIT))
    early = REG + timedelta(days=2)
    assert e007.score(samples, snaps, out, REG, early, 20) is None  # Pending
    late = REG + timedelta(days=8)
    res = e007.score(samples, snaps, out, REG, late, 20, ledger_path=out / "none.md")
    assert res["verdict"].startswith("Unavailable") and len(res["qualifying_periods"]) == 1
    assert (out / "results.json").exists()
    assert res["provenance"]["dev_fit_sha256_recorded_in_ledger"] is False
    with pytest.raises(FileExistsError):
        e007.score(samples, snaps, out, REG, late, 20)


def test_unavailable_when_nonzero_total_below_2000(roots, monkeypatch):
    samples, snaps = roots
    _caps(snaps, [("a", _h(1)), ("b", _h(2)), ("c", _h(3))])
    _write_sample(samples, "s1", "a", _h(1), _h(1.1))
    _write_sample(samples, "s2", "b", _h(2), _h(2.1))
    monkeypatch.setattr(e007, "N_PERIODS", 2)
    out = snaps / "e007"
    out.mkdir()
    (out / "dev_fit.json").write_text(json.dumps(FIT))
    res = e007.score(samples, snaps, out, REG, REG + timedelta(days=1), 20)
    assert res["verdict"].startswith("Unavailable") and res["nonzero_total"] == 2 * N
