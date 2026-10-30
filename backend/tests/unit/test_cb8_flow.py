# ruff: noqa: E501
"""CB8-W fetch and seal: window draw, per-event cap, split, exclusion, resumable chunks, capped / failed days, HOLDOUT separation,
no raw wallet or outcome field, seal-time drops, seal re-hash. Mocked HTTP only."""

from __future__ import annotations

import csv
import gzip
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from astrolabe.research_lab import cb8_common as cm
from astrolabe.research_lab import cb8_flow as f
from astrolabe.research_lab import h5_seal
from tests.unit._cb8_fakes import (
    RAW_PREFIX,
    Api,
    all_bytes,
    fingerprint_and_sha,
    make_key,
    nosleep,
    print_row,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import run_cb8 as script  # noqa: E402

D = datetime(2026, 8, 10, 6, tzinfo=UTC)


def iso(t: datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def gm(i, *, event=None, end=D, created=None, q=None, fee="politics_fees", volume=80000.0, neg="", series=()):
    cr = created or end - timedelta(days=40)
    return {"id": f"w{i}", "conditionId": f"wc{i}", "clobTokenIds": json.dumps([f"t{i}a", f"t{i}b"]), "createdAt": iso(cr), "startDate": iso(cr),
            "endDate": iso(end), "closed": True, "closedTime": iso(end), "question": q or f"Will thing {i} happen?", "slug": f"thing-{i}", "feeType": fee,
            "outcomes": '["Yes","No"]', "outcomePrices": '["0","1"]', "umaResolutionStatus": "resolved", "volumeNum": volume, "liquidityNum": 10.0,
            "negRisk": bool(neg), "negRiskMarketID": neg or None,
            "events": [{"id": str(event if event is not None else f"E{i}"), "title": f"event {i}", "series": [{"id": str(s)} for s in series], "tags": []}]}


def write_keys(path: Path, rows: list[dict], disjointness: str = "verified") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["market_id", "found", "event_ids", "neg_risk_market_id", "series_ids"])
        w.writeheader()
        w.writerows(rows)
    path.with_name("exclusion_report.json").write_text(json.dumps({"keys_sha256": h5_seal.sha256_file(path), "disjointness": disjointness}))


class Env:
    def __init__(self, tmp: Path):
        self.tmp = tmp
        self.key = cm.load_wallet_key_strict(make_key(tmp))
        self.sha, self.fp = fingerprint_and_sha("flow", self.key)
        self.root = tmp / "history"
        self.keys = tmp / "creative_batch8" / "exclusion_keys.csv.gz"
        write_keys(self.keys, [{"market_id": "w900", "found": "1", "event_ids": "EX1", "neg_risk_market_id": "NEGX", "series_ids": "SX"}])
        self.api = Api()
        mk = [gm(0), gm(1, event="EV"), gm(2, event="EV"), gm(3, event="EV"), gm(4, q="Bitcoin Up or Down on August 10?"), gm(5, fee="weather_fees"),
              gm(6, created=D - timedelta(days=5)), gm(7, volume=1000.0), gm(8, end=D.replace(year=2026, month=4)), gm(900), gm(901, event="EX1"),
              gm(902, neg="NEGX"), gm(903, series=("SX",))]
        mk += [gm(20 + i, end=D + timedelta(days=i % 9, hours=i), fee="sports_fees" if i % 4 == 0 else "politics_fees") for i in range(16)]
        for m in mk:
            self.api.gamma[m["id"]] = m
        self.smoke = tmp / "smoke.json"
        self.smoke.write_text(json.dumps({"criterion_a_data_api_paging": True}))

    def fetch(self, **kw):
        args = dict(key=self.key, fp=self.fp, rules_sha=self.sha, exclusion_keys_path=self.keys, smoke_path=self.smoke, n_main=10, n_sports=3, rps=100.0,
                    sleep=nosleep, now=D.timestamp() + 90 * 86400)
        args.update(kw)
        return f.flow_fetch(self.root, f.RUN_ID, self.api, **args)

    def add_prints(self):
        sample = f._read_sample(self.root / f.RUN_ID / "sample.csv.gz")
        for r in sample:
            w0 = r["w0_epoch"]
            self.api.trades[r["condition_id"]] = [print_row(r["condition_id"], w0 + 100 + 3000 * k, idx=k % 2, side="BUY" if k % 3 else "SELL", price=0.3 + 0.01 * k,
                                                            wallet=f"{RAW_PREFIX}_{r['market_id']}_{k % 3}") for k in range(8)]
        return sample


@pytest.fixture
def env(tmp_path):
    return Env(tmp_path)


def first_print_call(api) -> int:
    return next((i for i, c in enumerate(api.calls) if c[0].endswith("/trades")), len(api.calls))


def last_market_call(api) -> int:
    return max((i for i, c in enumerate(api.calls) if c[0].endswith("/markets")), default=-1)


# ---- rules: window, cap, split, sample ------------------------------------------------------------------------------------------------------


def row(i, **kw):
    r = {"market_id": f"m{i}", "event_ids": f"E{i // 2}", "event_id": f"E{i // 2}", "created_at": "2026-06-01T00:00:00Z", "start_at": "2026-06-01T00:00:00Z",
         "end_epoch": cm.ep("2026-08-01T00:00:00Z"), "topic": "politics", "fee_category": "politics"}
    r.update(kw)
    return r


def test_draw_window_range_determinism_and_empty():
    r = row(1)
    w = f.draw_window(r)
    assert w == f.draw_window(r) and w[1] - w[0] == int(74.5 * 3600)
    lo = max(cm.ep("2026-06-01T00:00:00Z") + 86400, cm.ep(f.WINDOW_FLOOR))
    hi = min(r["end_epoch"] - 4 * 86400, cm.ep(f.WINDOW_LAST_END)) - 72 * 3600
    assert lo <= w[0] <= hi
    assert f.draw_window(row(1, end_epoch=cm.ep("2026-06-03T00:00:00Z"))) is None
    spread = {f.draw_window(row(i))[0] for i in range(40)}
    assert len(spread) > 30  # uniform over the range, not a fixed offset
    late = f.draw_window(row(2, end_epoch=cm.ep("2026-09-30T00:00:00Z")))
    assert late[1] <= cm.ep(f.HIST_END)


def test_per_event_cap_split_and_sample_are_id_seeded():
    rows = [row(i, event_ids="EV") for i in range(5)] + [row(10 + i) for i in range(4)]
    kept, dropped = f.per_event_cap(rows)
    assert dropped == 3 and sum(1 for r in kept if r["event_ids"] == "EV") == 2
    kept2, _ = f.per_event_cap(list(reversed(rows)))
    assert [r["market_id"] for r in kept] == [r["market_id"] for r in kept2]
    assert {f.event_split(r) for r in [row(i, event_ids=f"E{i}") for i in range(30)]} == {"screen", "holdout"}
    assert f.event_split(row(1)) == f.event_split(row(1, market_id="other"))  # same event, same side
    s, rep = f.flow_sample([row(i, event_ids=f"E{i}", topic="sports" if i < 5 else "politics") for i in range(30)], 10, 3)
    assert sum(r["group"] == "sports" for r in s) == 3 and sum(r["group"] == "main" for r in s) == 10 and rep["groups"]["main"]["pool"] == 25
    assert len({r["market_id"] for r in s}) == 13


def test_day_segments_cover_the_window_exactly():
    w0 = int(cm.ep("2026-08-01T22:30:00Z"))
    segs = f.day_segments(w0, w0 + int(74.5 * 3600))
    assert [s[0] for s in segs] == ["2026-08-01", "2026-08-02", "2026-08-03", "2026-08-04", "2026-08-05"]
    assert segs[0][1] == w0 and segs[-1][2] == w0 + int(74.5 * 3600) - 1
    assert all(b[1] == a[2] + 1 for a, b in zip(segs, segs[1:], strict=False))


# ---- fetch ------------------------------------------------------------------------------------------------------------------------------------


def run_to_sample(env):
    """Frame walk until the sample exists; the print stage is stopped at once."""
    return env.fetch(should_stop=lambda: (env.root / f.RUN_ID / "sample.csv.gz").exists())


def test_frame_filters_drops_and_split_before_any_print_request(env):
    m = run_to_sample(env)
    assert m["status"] == "in_progress" and m["stopped"] == "should_stop"
    rdir = env.root / f.RUN_ID
    split = json.loads((rdir / "split.json").read_text())
    rep = split["report"]
    assert rep["filtered"] == {"life_below_min": 1, "volume_below_min": 1, "weather": 1, "crypto_updown": 1}
    assert rep["dropped_id"] == 1 and rep["dropped_keys"] == {"event": 1, "neg_risk_market": 1, "series": 1}
    sample = f._read_sample(rdir / "sample.csv.gz")
    ids = {r["market_id"] for r in sample}
    assert not ids & {"w900", "w901", "w902", "w903", "w4", "w5", "w6", "w7", "w8"} and len(ids) == 13
    assert sum(1 for r in sample if r["event_ids"] == "EV") == 2  # capped to two per event
    assert {k: v for k, v in split["events"].items() if k == "EV"}
    assert first_print_call(env.api) == len(env.api.calls) and not any(c[0].endswith("/trades") for c in env.api.calls)
    header = next(csv.reader(gzip.open(rdir / "sample.csv.gz", "rt")))
    assert not [c for c in header if "outcome" in c or "uma" in c or "closed" in c]
    assert RAW_PREFIX.encode() not in all_bytes(rdir)


def test_full_fetch_files_holdout_separation_manifest_and_resume(env):
    m = run_to_sample(env)
    sample = env.add_prints()
    # resume: stop after a few print requests, then finish
    calls = {"n": 0}

    def stop_after_5():
        calls["n"] += 1
        return calls["n"] > 5

    m = env.fetch(should_stop=stop_after_5)
    assert m["status"] == "in_progress" and m["stopped"] == "should_stop"
    m = env.fetch()
    assert m["status"] == f.COMPLETE and m["complete"] is True
    rdir = env.root / f.RUN_ID
    screen = {p.name[:-7] for p in (rdir / "screen").glob("*.csv.gz")}
    holdout = {p.name[:-7] for p in (rdir / "holdout").glob("*.csv.gz")}
    assert screen | holdout == {r["market_id"] for r in sample} and not screen & holdout and screen and holdout
    split = json.loads((rdir / "split.json").read_text())["events"]
    for r in sample:
        assert (r["market_id"] in holdout) == (split[f.event_key(r)] == "holdout")
    # each print request series is one per (market, UTC day segment); nothing is requested twice
    reqs = [(c[1]["market"], c[1]["start"]) for c in env.api.calls if c[0].endswith("/trades")]
    assert len(reqs) == len(set(reqs))
    rows = list(csv.DictReader(gzip.open(next((rdir / "screen").glob("*.csv.gz")), "rt")))
    assert rows and set(rows[0]) == set(f.PRINT_COLUMNS) and all(len(r["wallet_hash"]) == 32 for r in rows)
    w = next(r for r in sample if r["market_id"] == next((rdir / "screen").glob("*.csv.gz")).name[:-7])
    assert all(w["w0_epoch"] <= int(r["ts"]) < w["window_end_epoch"] for r in rows)  # every stored print lies inside its market window
    days = list(csv.DictReader(gzip.open(rdir / "days.csv.gz", "rt")))
    assert {d["status"] for d in days} == {"ok"}
    man = json.loads((rdir / "manifest.json").read_text())
    assert man["wallet_key_fingerprint"] == env.fp and man["rules_sha256"] == env.sha and man["state"]["exclusion_keys_sha256"]
    assert {"sample.csv.gz", "split.json", "frame.csv.gz", "days.csv.gz"} <= set(man["file_sha256"]) and cm.verify_manifest_files(rdir, man) == len(man["file_sha256"])
    assert RAW_PREFIX.encode() not in all_bytes(rdir)
    assert env.fetch()["status"] == f.COMPLETE  # sticky, no new requests
    n = len(env.api.calls)
    env.fetch()
    assert len(env.api.calls) == n
    assert m["counts"]["n_sample"] == 13


def test_capped_failed_and_no_data_days_are_kept_apart(env, monkeypatch):
    run_to_sample(env)
    sample = env.add_prints()
    target, bad, empty = sample[0], sample[1], sample[2]
    env.api.trades[target["condition_id"]] = [print_row(target["condition_id"], target["w0_epoch"] + 10 + i, wallet=f"0xw{i}") for i in range(40)]
    monkeypatch.setattr(f, "PRINT_LIMIT", 10)
    env.api.fail_trades.add(bad["condition_id"])
    env.api.trades[empty["condition_id"]] = []
    statuses = []
    for _ in range(6):
        m = env.fetch(day_pages=2)
        statuses.append(m["status"])
        if m["status"] == f.COMPLETE:
            break
    assert statuses[-1] == f.COMPLETE and statuses[0] == "in_progress"
    days = list(csv.DictReader(gzip.open(env.root / f.RUN_ID / "days.csv.gz", "rt")))
    by = {}
    for d in days:
        by.setdefault(d["market_id"], set()).add(d["status"])
    assert "capped" in by[target["market_id"]] and by[bad["market_id"]] == {"failed"} and by[empty["market_id"]] == {"ok"}
    folder = "holdout" if json.loads((env.root / f.RUN_ID / "split.json").read_text())["events"][f.event_key(target)] == "holdout" else "screen"
    rows = list(csv.DictReader(gzip.open(env.root / f.RUN_ID / folder / f"{target['market_id']}.csv.gz", "rt")))
    assert rows == []  # the capped day is unavailable: its prints are not stored
    man = json.loads((env.root / f.RUN_ID / "manifest.json").read_text())
    assert man["counts"]["n_day_failed"] >= 1 and man["counts"]["n_day_capped"] >= 1 and man["counts"]["n_day_empty"] >= 1


def test_guards_smoke_exclusion_files_disk_and_headroom(env, tmp_path):
    with pytest.raises(cm.Refused, match="not found"):
        env.fetch(smoke_path=tmp_path / "none.json")
    env.smoke.write_text(json.dumps({"criterion_a_data_api_paging": False}))
    with pytest.raises(cm.Refused, match="paging"):
        env.fetch()
    env.smoke.write_text(json.dumps({"criterion_a_data_api_paging": True}))
    with pytest.raises(cm.Refused):
        env.fetch(exclusion_keys_path=tmp_path / "none.csv.gz")
    env.keys.write_bytes(env.keys.read_bytes() + b"tamper")  # keys file no longer matches its report
    with pytest.raises(cm.Refused, match="sha256"):
        env.fetch()
    write_keys(env.keys, [])
    with pytest.raises(cm.Refused):
        f.flow_fetch(tmp_path / "cb7_extract", f.RUN_ID, env.api, key=env.key, fp=env.fp, rules_sha=env.sha, exclusion_keys_path=env.keys, smoke_path=env.smoke)
    with pytest.raises(cm.Refused):
        f.flow_fetch(env.root, "h8_geo", env.api, key=env.key, fp=env.fp, rules_sha=env.sha, exclusion_keys_path=env.keys, smoke_path=env.smoke)
    with pytest.raises(cm.NotNow, match="headroom"):
        env.fetch(data_dumps=tmp_path, data_dumps_cap_gb=0.0)
    assert not (env.root / f.RUN_ID).exists() or not list((env.root / f.RUN_ID).glob("manifest.json"))
    m = env.fetch(disk_cap=1)
    assert m["status"] == cm.DISK_BUDGET_TOKEN
    n = len(env.api.calls)
    assert env.fetch()["status"] == cm.DISK_BUDGET_TOKEN and len(env.api.calls) == n


def test_other_fingerprint_is_refused_on_an_existing_run(env):
    run_to_sample(env)
    other = "7" * 16
    with pytest.raises(cm.Refused, match="fingerprint"):
        env.fetch(fp=other, rules_sha=cm.rules_file_doc("flow", other)["rules_sha256"])


def test_unverified_exclusion_report_ends_the_run(env):
    write_keys(env.keys, [], disjointness="disjointness_unverified")
    m = env.fetch()
    assert m["status"] == f.UNVERIFIED and (env.root / f.RUN_ID / "DISJOINTNESS_UNVERIFIED.json").exists()
    assert not (env.root / f.RUN_ID / "sample.csv.gz").exists()
    assert env.fetch()["status"] == f.UNVERIFIED


# ---- seal -------------------------------------------------------------------------------------------------------------------------------------


def complete_run(env):
    run_to_sample(env)
    sample = env.add_prints()
    assert env.fetch()["status"] == f.COMPLETE
    return sample


def seal_kwargs(env, seals):
    return dict(fp=env.fp, transport=env.api, seals_dir=seals, trials_path=env.tmp / "trials.jsonl", sleep=nosleep)


def test_seal_drops_by_id_and_key_records_holdout_listing_and_verifies(env, tmp_path):
    sample = complete_run(env)
    seals = tmp_path / "seals"
    seals.mkdir()
    victim_id = sample[0]["market_id"]
    twin = gm(950, event=sample[1]["event_ids"].split(";")[0])  # a market of an older sealed run that shares an event with a sample market
    env.api.gamma["w950"] = twin
    (seals / "h6_weather_SEAL.json").write_text(json.dumps({"files": {f"prices/{victim_id}.csv.gz": "x", "trades/w950.csv.gz": "y", "manifest.json": "z"}}))
    res = f.flow_seal(env.root, **seal_kwargs(env, seals))
    assert res["sealed"] and res["drop_counts"]["DROPPED_SEAL_COPIES"] >= 2 and res["disjointness"] == "verified"
    rdir = env.root / f.RUN_ID
    drops = list(csv.DictReader(gzip.open(rdir / "drops.csv.gz", "rt")))
    reasons = {d["market_id"]: d["reason"] for d in drops}
    assert reasons[victim_id].startswith("id") and any("event" in v for v in reasons.values())
    assert (seals / "h9_flow_SEAL.json").exists() and h5_seal.verify_seal(rdir)["listing_sha256"] == res["listing_sha256"]
    rep = json.loads((rdir / "drops_report.json").read_text())
    assert rep["holdout_listing_sha256"] == res["holdout_listing_sha256"] and rep["seal_copies_read"] == ["h6_weather_SEAL.json"]
    sample_after = f._read_sample(rdir / "sample.csv.gz")
    assert len(sample_after) == len(sample)  # sealed files are never edited; drops are recorded only
    with pytest.raises(cm.Refused, match="already sealed"):
        f.flow_seal(env.root, **seal_kwargs(env, seals))
    assert json.loads((env.tmp / "trials.jsonl").read_text().splitlines()[-1])["n_tests"] == 0


def test_seal_refuses_incomplete_tampered_or_other_fingerprint(env, tmp_path):
    run_to_sample(env)
    seals = tmp_path / "seals"
    seals.mkdir()
    with pytest.raises(cm.NotNow):
        f.flow_seal(env.root, **seal_kwargs(env, seals))
    env.add_prints()
    env.fetch()
    kw = seal_kwargs(env, seals)
    with pytest.raises(cm.Refused, match="fingerprint"):
        f.flow_seal(env.root, **{**kw, "fp": "5" * 16})
    victim = next((env.root / f.RUN_ID / "screen").glob("*.csv.gz"), None) or next((env.root / f.RUN_ID / "holdout").glob("*.csv.gz"))
    victim.write_bytes(victim.read_bytes() + b"x")
    with pytest.raises(cm.Refused, match="differs"):
        f.flow_seal(env.root, **kw)
    assert not (env.root / f.RUN_ID / "SEAL.json").exists()


def test_seal_unverified_when_drop_metadata_is_missing(env, tmp_path):
    complete_run(env)
    seals = tmp_path / "seals"
    seals.mkdir()
    (seals / "h5_cb1_SEAL.json").write_text(json.dumps({"files": {"prices/nometa1.csv.gz": "x", "prices/nometa2.csv.gz": "y"}}))
    res = f.flow_seal(env.root, **seal_kwargs(env, seals))
    assert res["disjointness"] == f.UNVERIFIED


# ---- CLI --------------------------------------------------------------------------------------------------------------------------------------


def test_cli_flow_fetch_guards(env, tmp_path):
    rules = tmp_path / "flow_rules.json"
    assert script.main(["rules", "--which", "flow", "--path", str(rules), "--wallet-key-path", str(tmp_path / "keydir" / "wallet_hash_key")]) == 0
    base = ["flow-fetch", "--rules", str(rules), "--allow-uncommitted-rules", "--root", str(env.root), "--data-dumps", str(tmp_path), "--disk-cap-gb", "0.15", "--standalone",
            "--wallet-key-path", str(tmp_path / "keydir" / "wallet_hash_key")]
    assert script.main([*base, "--n-main", "99"]) == 2  # declared argument changed
    assert script.main([*base, "--cap-at", "2026-10-22T00:00Z"]) == 2
    assert script.main([*base, "--wallet-key-path", str(tmp_path / "nokey")]) == 2
    assert script.main([*base, "--exclusion-keys", str(tmp_path / "none.csv.gz"), "--require-smoke", str(env.smoke)]) == 2
    assert script.main(["flow-seal", "--rules", str(rules), "--allow-uncommitted-rules", "--root", str(env.root), "--wallet-key-path", str(tmp_path / "nokey")]) == 2
