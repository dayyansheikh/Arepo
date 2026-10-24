# ruff: noqa: E501
"""Amendment A-T1 (CREATIVE_BATCH_6.md): the h8_tail_b top-up run and the union seal. Offline, fakes only."""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from astrolabe.research_lab import cb6_tail as t
from tests.unit import test_cb6_tail as base
from tests.unit.test_cb6_tail import (
    CUTOFF,
    DAY,
    END_FROM,
    KEY,
    NOW,
    SEED,
    FakeApi,
    World,
    ep,
    gm,
    iso,
    make_trades,
    read_csv_gz,
    slot_start,
    write_seal_copy,
)

script = base.script


def test_topup_windows_nest_under_the_frozen_seed():
    """h8_tail's single window is always among the nine picks of the same seed, for every day of the frame and every
    possible number of valid slots (a short last day), so the union equals the frozen 9-window frame."""
    days = [datetime(2025, 9, 1, tzinfo=UTC).date() + timedelta(days=i) for i in range(405)]
    checked = 0
    for d in days:
        dkey = f"{d:%Y-%m-%d}"
        for n in (96, 95, 60, 20, 9, 8, 3, 1):
            valid = list(range(n))
            one = t.window_picks(t.SEED, dkey, valid, 1)
            nine = t.window_picks(t.SEED, dkey, valid, 9)
            extra = t.topup_window_picks(t.SEED, dkey, valid, 9)
            assert len(one) == 1 and set(one) <= set(nine)
            assert set(extra) | set(one) == set(nine) and not set(extra) & set(one) and len(extra) == len(nine) - 1
            checked += 1
    assert checked == 405 * 8
    # the parent draw is exactly the pre-amendment inline draw
    assert t.window_picks(t.SEED, "2026-04-01", list(range(96)), 1) == sorted(random.Random(f"{t.SEED}|2026-04-01").sample(list(range(96)), 1))
    assert t.topup_window_picks(t.SEED, "2026-04-01", [], 9) == []


def test_topup_refuses_when_windows_do_not_nest(monkeypatch):
    monkeypatch.setattr(t, "window_picks", lambda seed, dkey, valid, k: [5] if k == 1 else [1, 2, 3])
    with pytest.raises(t.Refused, match="nest"):
        t.topup_window_picks(t.SEED, "2026-04-01", list(range(96)), 9)


def b_markets(n_days=8, start_id=200001):
    """Markets in windows the parent did NOT walk (the top-up picks): three per day."""
    days = [datetime(2026, 4, 1, tzinfo=UTC).date() + timedelta(days=i) for i in range(n_days)]
    out, nid = [], start_id
    for d in days:
        dkey = f"{d:%Y-%m-%d}"
        d0 = datetime(d.year, d.month, d.day, tzinfo=UTC)
        valid = [k for k in range(96) if (d0 + timedelta(minutes=(k + 1) * 15)).timestamp() <= CUTOFF]
        for k in t.topup_window_picks(SEED, dkey, valid, 9)[:3]:
            nid += 1
            out.append(gm(nid, (d0 + timedelta(minutes=k * 15)).timestamp() + 60))
    return out


def add_markets(w, ms):
    for m in ms:
        w.api.markets[m["id"]] = m
        w.api.trades[m["conditionId"]] = make_trades(m["id"], ep(m["createdAt"]), ep(m["endDate"]))


def run_b(w, *, api=None, **kw):
    cfg = dict(history_root=w.root, seals_dir=w.seals, rules_path=w.rules, pins=w.pins, n_markets=w.n_markets, end_from=END_FROM,
               rps=4.0, key=KEY, now=NOW + 9 * DAY, sleep=lambda s: None, live_check=None, require_committed=False,
               require_smoke=False, wall_clock=lambda: NOW + 3600, disk_cap=int(0.25 * 1024**3), windows_per_day=9, topup_of=t.RUN_ID)
    cfg.update(kw)
    return t.tail_fetch(w.root, t.RUN_ID_B, api or w.api, **cfg)


@pytest.fixture()
def topup_world(tmp_path):
    w = World(tmp_path, n_markets=4500)
    assert w.run()["status"] == t.COMPLETE_TOKEN
    bm = b_markets()
    add_markets(w, bm)
    return w, bm


def test_topup_pins_clock_walks_only_new_windows_and_excludes_parent_by_id(topup_world):
    w, bm = topup_world
    parent_rows = read_csv_gz(w.rdir / "sample.csv.gz")
    pid = parent_rows[0]["market_id"]
    parent_listing = t.file_hashes(w.rdir)
    w.api.markets[pid]["endDate"] = bm[0]["endDate"]  # the parent's market now sits in a window b walks: excluded by id only
    n0 = len(w.api.log)
    m = run_b(w)
    assert m["status"] == t.COMPLETE_TOKEN
    bdir = w.root / t.RUN_ID_B
    clock = json.loads((bdir / "request_clock.json").read_text())["request_clock_epoch"]
    assert clock == json.loads((w.rdir / "request_clock.json").read_text())["request_clock_epoch"] == NOW  # NOT NOW + 9 d
    man = json.loads((bdir / "manifest.json").read_text())
    assert man["request_clock_now"] == iso(NOW) and man["params"]["windows_per_day"] == 9
    tp = man["params"]["topup"]
    assert tp["parent"] == "h8_tail" and tp["request_clock_utc"] == iso(NOW) and tp["parent_sample_sha256"] == parent_listing["sample.csv.gz"]
    rep = json.loads((bdir / "frame_report.json").read_text())
    assert rep["t_fetch8"] == iso(NOW) and rep["end_cutoff"] == iso(CUTOFF) and rep["windows_per_day"] == 9
    assert rep["parent_id_dropped"] == 1 and rep["topup"]["parent_n_sample"] == len(parent_rows)
    ids_b = {r["market_id"] for r in read_csv_gz(bdir / "sample.csv.gz")}
    assert pid not in ids_b and ids_b and not ids_b & {r["market_id"] for r in parent_rows}
    walked = [(ep(p["end_date_min"]), p["closed"]) for k, p in w.api.log[n0:] if k == "gamma_window"]
    days = {datetime.fromtimestamp(x, UTC).date() for x, _ in walked}
    assert {slot_start(d) for d in days}.isdisjoint({x for x, _ in walked})  # never one of the parent's windows
    assert len(walked) == 2 * 8 * len(days)  # 8 windows per day, both closed passes
    assert t.file_hashes(w.rdir) == parent_listing  # parent listing unchanged
    log = [json.loads(x) for x in (w.rdir / "ACCESS_LOG.jsonl").read_text().splitlines()]
    assert log and log[0]["files"] == ["sample.csv.gz"]  # the read of the parent sample is logged
    assert json.loads((bdir / "exclusion_report.json").read_text())["n_ids"] == len(w.excl_ids)  # parent keys not excluded
    assert rep["outcomes_censored_post_cap"] == 0
    for o in read_csv_gz(bdir / "origins.csv.gz"):
        assert float(o["origin_ts"]) <= NOW - 60 * DAY


def test_topup_refuses_unless_parent_complete_unsealed_and_unchanged(tmp_path):
    w = World(tmp_path)
    with pytest.raises(t.Refused, match="no manifest"):
        run_b(w)
    w.run(should_stop=lambda: len([1 for k, _ in w.api.log if k == "prices"]) >= 3)
    with pytest.raises(t.Refused, match="not tail_fetch_complete"):
        run_b(w)
    assert w.run()["status"] == t.COMPLETE_TOKEN
    good = (w.rdir / "sample.csv.gz").read_bytes()
    (w.rdir / "sample.csv.gz").write_bytes(good + b" ")
    with pytest.raises(t.Refused, match="sha256"):
        run_b(w)
    (w.rdir / "sample.csv.gz").write_bytes(good)
    for bad in (dict(windows_per_day=1), dict(topup_of=None), dict(seed="other")):
        with pytest.raises(t.Refused):
            run_b(w, **bad)
    with pytest.raises(t.Refused):
        w.run(topup_of=t.RUN_ID)  # h8_tail itself is not a top-up
    (w.rdir / "SEAL.json").write_text("{}")
    with pytest.raises(t.Refused, match="sealed"):
        run_b(w)
    assert t.refuse_run_id(t.RUN_ID_B) == t.RUN_ID_B
    with pytest.raises(t.Refused):
        t.refuse_run_id("h8_tail_c")


def test_topup_pinned_clock_cannot_drift(topup_world):
    w, _ = topup_world
    (w.root / t.RUN_ID_B).mkdir()
    (w.root / t.RUN_ID_B / "request_clock.json").write_text(json.dumps({"request_clock_epoch": NOW + 5, "request_clock_utc": "x"}))
    with pytest.raises(t.Refused, match="pinned to the parent"):
        run_b(w)


def test_topup_union_pool_uses_the_frozen_sampler_when_it_exceeds_n(topup_world):
    w, _ = topup_world
    n_parent = len(read_csv_gz(w.rdir / "sample.csv.gz"))
    run_b(w, n_markets=n_parent + 3)
    rep = json.loads((w.root / t.RUN_ID_B / "frame_report.json").read_text())
    assert rep["sample"]["union_pool_exceeds_n_markets"] is True and rep["sample"]["taken_all"] is False
    assert rep["sample"]["parent_in_pool"] == n_parent and rep["n_sample"] == len(read_csv_gz(w.root / t.RUN_ID_B / "sample.csv.gz"))
    assert rep["n_sample"] < rep["sample"]["own_pool"]


def _h7_done(w):
    write_seal_copy(w.seals / "h7_cb4_era_SEAL.json", [])
    (w.seals / "h7_cb4_series_NOT_RUN.json").write_text("{}")


def test_topup_every_non_complete_ending_drops_it_and_h8_tail_seals_alone(topup_world):
    w, _ = topup_world
    _h7_done(w)
    kw = dict(seals_dir=w.seals, sleep=lambda s: None, topup_run_id=t.RUN_ID_B, trials_path=w.tmp / "tr.jsonl")
    with pytest.raises(t.NotNow):  # not started, before T_seal: pending
        t.seal_tail(w.root, t.RUN_ID, **kw)
    assert run_b(w, wall_clock=lambda: t.T_SEAL_EPOCH + 1)["status"] == t.NOT_RUN_TOKEN  # a chunk at or after T_seal: not run
    res = t.seal_tail(w.root, t.RUN_ID, **kw)
    assert res["sealed"] and res["topup"] == {"run_id": "h8_tail_b", "status": "dropped", "reason": t.NOT_RUN_TOKEN, "refusal_reason": "none"}
    seal = json.loads((w.rdir / "SEAL.json").read_text())
    assert seal["topup"]["status"] == "dropped" and "files" not in seal["topup"]
    assert t.verify_tail(w.root, t.RUN_ID, w.seals)["listing_sha256"] == seal["listing_sha256"]
    split = read_csv_gz(w.rdir / "split.csv.gz")
    assert {r["market_id"] for r in split} == {r["market_id"] for r in read_csv_gz(w.rdir / "sample.csv.gz")}
    assert set(split[0]) == {"market_id", "event_key", "block"}  # h8_tail-alone format unchanged
    assert len((w.tmp / "tr.jsonl").read_text().splitlines()) == 1


@pytest.mark.parametrize("ending", ["disk_budget", "unverified", "incomplete_after_t_seal", "never_started_after_t_seal"])
def test_topup_state_classifies_every_non_complete_ending_as_dropped(topup_world, ending):
    w, _ = topup_world
    late = lambda: t.T_SEAL_EPOCH + 5  # noqa: E731
    if ending == "disk_budget":
        run_b(w, disk_cap=60_000)
        assert json.loads((w.root / t.RUN_ID_B / "manifest.json").read_text())["status"] == t.DISK_BUDGET_TOKEN
        assert t.topup_state(w.root, t.RUN_ID_B, wall_clock=lambda: NOW)[0] == "dropped"
    elif ending == "unverified":
        (w.root / t.RUN_ID_B).mkdir()
        (w.root / t.RUN_ID_B / t.UNVERIFIED_FILE).write_text("{}")
        assert t.topup_state(w.root, t.RUN_ID_B, wall_clock=lambda: NOW) == ("dropped", t.UNVERIFIED_TOKEN)
    elif ending == "incomplete_after_t_seal":
        run_b(w, should_stop=lambda: len([1 for k, _ in w.api.log if k == "prices"]) >= 3)
        assert t.topup_state(w.root, t.RUN_ID_B, wall_clock=lambda: NOW)[0] == "pending"
        assert t.topup_state(w.root, t.RUN_ID_B, wall_clock=late) == ("dropped", t.NOT_RUN_TOKEN)
        assert (w.root / t.RUN_ID_B / t.NOT_RUN_FILE).exists()
    else:
        assert t.topup_state(w.root, t.RUN_ID_B, wall_clock=late) == ("dropped", "never_started_by_T_seal")


def test_topup_disjointness_unverified_in_a_real_run_is_terminal(tmp_path):
    w = World(tmp_path)
    assert w.run()["status"] == t.COMPLETE_TOKEN
    for mid in w.excl_ids[:10]:
        w.api.markets[mid]["hide"] = True
    m = run_b(w)
    assert m["status"] == t.UNVERIFIED_TOKEN
    assert t.topup_state(w.root, t.RUN_ID_B, wall_clock=lambda: NOW) == ("dropped", t.UNVERIFIED_TOKEN)
    assert not (w.root / t.RUN_ID_B / "sample.csv.gz").exists()


def _union_ready(w, tmp_path):
    assert run_b(w)["status"] == t.COMPLETE_TOKEN
    _h7_done(w)
    return dict(seals_dir=w.seals, sleep=lambda s: None, trials_path=tmp_path / "trials.jsonl")


def test_union_seal_covers_both_runs_and_verify_checks_both(topup_world, tmp_path):
    w, _ = topup_world
    kw = _union_ready(w, tmp_path)
    with pytest.raises(t.Refused, match="union is used whenever it completes"):
        t.seal_tail(w.root, t.RUN_ID, **kw)  # sealing h8_tail alone next to a complete top-up is refused
    res = t.seal_tail(w.root, t.RUN_ID, topup_run_id=t.RUN_ID_B, **kw)
    a_ids = {r["market_id"] for r in read_csv_gz(w.rdir / "sample.csv.gz")}
    b_ids = {r["market_id"] for r in read_csv_gz(w.root / t.RUN_ID_B / "sample.csv.gz")}
    split = read_csv_gz(w.rdir / "split.csv.gz")
    assert {r["market_id"] for r in split} == a_ids | b_ids and not a_ids & b_ids
    assert {r["run"] for r in split} == {"h8_tail", "h8_tail_b"}
    assert sum(res["split_counts"].values()) == len(a_ids) + len(b_ids)
    seal = json.loads((w.rdir / "SEAL.json").read_text())
    tp = seal["topup"]
    assert tp["status"] == "complete" and tp["files"] and tp["union_listing_sha256"] == seal["declaration"]["topup"]["union_listing_sha256"]
    assert len(kw["trials_path"].read_text().splitlines()) == 1
    assert (w.seals / "h8_tail_SEAL.json").read_bytes() == (w.rdir / "SEAL.json").read_bytes()
    assert not (w.root / t.RUN_ID_B / "SEAL.json").exists()
    assert t.verify_tail(w.root, t.RUN_ID, w.seals)["topup"]["status"] == "complete"
    paths = t.read_tail_sealed(w.root, t.RUN_ID, "unit", ["sample.csv.gz"], w.seals)
    assert {p.parent.name for p in paths} == {"h8_tail", "h8_tail_b"}
    f = w.root / t.RUN_ID_B / "origins.csv.gz"  # b is covered by the verification
    good = f.read_bytes()
    f.write_bytes(good + b"x")
    with pytest.raises(t.SealError, match="top-up verification"):
        t.verify_tail(w.root, t.RUN_ID, w.seals)
    f.write_bytes(good)
    (w.root / t.RUN_ID_B / "stray.txt").write_text("x")
    with pytest.raises(t.SealError):
        t.read_tail_sealed(w.root, t.RUN_ID, "unit", ["sample.csv.gz"], w.seals)
    (w.root / t.RUN_ID_B / "stray.txt").unlink()
    assert t.verify_tail(w.root, t.RUN_ID, w.seals)


def test_union_seal_refuses_overlap_clock_skew_and_changed_files(topup_world, tmp_path):
    w, _ = topup_world
    kw = _union_ready(w, tmp_path)
    bdir = w.root / t.RUN_ID_B
    mp = bdir / "manifest.json"
    good = mp.read_text()
    man = json.loads(good)
    man["request_clock_now"] = iso(NOW + 3600)
    mp.write_text(json.dumps(man))
    with pytest.raises(t.Refused, match="request clock"):
        t.seal_tail(w.root, t.RUN_ID, topup_run_id=t.RUN_ID_B, **kw)
    mp.write_text(good)
    f = bdir / "origins.csv.gz"
    orig = f.read_bytes()
    f.write_bytes(orig + b"x")
    with pytest.raises(t.Refused, match="sha256"):
        t.seal_tail(w.root, t.RUN_ID, topup_run_id=t.RUN_ID_B, **kw)
    f.write_bytes(orig)
    arows = read_csv_gz(w.rdir / "sample.csv.gz")  # a shared market id: a parent row planted in b's sample (manifest re-pinned)
    brows = read_csv_gz(bdir / "sample.csv.gz")
    buf = io.StringIO()
    wr = csv.DictWriter(buf, fieldnames=list(brows[0].keys()))
    wr.writeheader()
    wr.writerows([*brows, {**brows[0], "market_id": arows[0]["market_id"]}])
    (bdir / "sample.csv.gz").write_bytes(gzip.compress(buf.getvalue().encode()))
    man = json.loads(good)
    man["file_sha256"]["sample.csv.gz"] = hashlib.sha256((bdir / "sample.csv.gz").read_bytes()).hexdigest()
    mp.write_text(json.dumps(man))
    with pytest.raises(t.Refused, match="share"):
        t.seal_tail(w.root, t.RUN_ID, topup_run_id=t.RUN_ID_B, **kw)


def test_union_h7_drops_and_event_split_run_over_both_runs(topup_world, tmp_path):
    w, _ = topup_world
    kw = _union_ready(w, tmp_path)
    brow = read_csv_gz(w.root / t.RUN_ID_B / "sample.csv.gz")[0]
    arow = read_csv_gz(w.rdir / "sample.csv.gz")[0]
    api = FakeApi([gm("777002", ep("2026-05-01T00:00:00Z"), event=arow["event_ids"].split(";")[0]),
                   gm(brow["market_id"], ep("2026-05-01T00:00:00Z"))])
    write_seal_copy(w.seals / "h7_cb4_era_SEAL.json", ["777002", brow["market_id"]])
    res = t.seal_tail(w.root, t.RUN_ID, topup_run_id=t.RUN_ID_B, transport=api, **kw)
    split = {r["market_id"]: r for r in read_csv_gz(w.rdir / "split.csv.gz")}
    assert split[brow["market_id"]]["block"] == "DROPPED_H7" and split[arow["market_id"]]["block"] == "DROPPED_H7"
    assert split[brow["market_id"]]["run"] == "h8_tail_b" and res["h7_dropped"] >= 2


def test_shared_event_across_runs_gets_one_split_block():
    rows = [{"market_id": "1", "event_ids": "E9", "neg_risk_market_id": "", "_run": "h8_tail"},
            {"market_id": "2", "event_ids": "E9", "neg_risk_market_id": "", "_run": "h8_tail_b"}]
    sp = t.event_key_split(rows)
    assert sp["1"] == sp["2"]


def test_smoke_carry_over_is_explicit_pinned_and_tested(tmp_path):
    v2 = t.SMOKE_CARRY_OVER["from_rules_sha256"]
    p = tmp_path / "s.json"
    doc = {"pass": True, "rules_sha256": v2, "smoke_version": "h8-tail-smoke-v2"}
    p.write_text(json.dumps(doc))
    with pytest.raises(t.Refused):  # right old hash but not the pinned file: no silent bypass
        t.smoke_ok(p, "newhash")
    pin = dict(t.SMOKE_CARRY_OVER, smoke_file_sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    assert t.smoke_ok(p, "newhash", pin)["carried_over_to_rules_sha256"] == "newhash"
    with pytest.raises(t.Refused):  # carry-over only from the declared hash
        t.smoke_ok(p, "newhash", None)
    p.write_text(json.dumps({**doc, "rules_sha256": "other"}))
    with pytest.raises(t.Refused):
        t.smoke_ok(p, "newhash", dict(pin, smoke_file_sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    real = Path(__file__).resolve().parents[3] / t.SMOKE_CARRY_OVER["smoke_file"]
    if real.exists():
        assert hashlib.sha256(real.read_bytes()).hexdigest() == t.SMOKE_CARRY_OVER["smoke_file_sha256"]
        assert t.smoke_ok(real, t.rules_file_doc()["rules_sha256"])["pass"] is True


def test_v3_rules_keep_every_v2_rule_function_and_v2_file():
    import inspect

    if not t.RULES_FILE_V2.exists():
        pytest.skip("v2 rules file not present")
    v2 = json.loads(t.RULES_FILE_V2.read_text())
    assert v2["rules_sha256"] == t.SMOKE_CARRY_OVER["from_rules_sha256"] and t.RULES_FILE != t.RULES_FILE_V2
    old = hashlib.sha256("\n".join(inspect.getsource(f) for f in t.RULE_FUNCS if f.__name__ not in ("window_picks", "topup_window_picks")).encode()).hexdigest()
    assert old == v2["funcs_sha256"]  # no v2 rule function changed: only the top-up section and its two functions were added
    d3 = t.rules_doc()
    assert {k for k in d3 if d3[k] != v2.get(k)} == {"rules_version", "smoke", "topup", "funcs_sha256"}


def test_runner_declares_the_topup_run_and_cap_flag(tmp_path):
    ap = script.build_parser()
    a = ap.parse_args(["tail-fetch", "--run-id", "h8_tail_b", "--topup-of", "h8_tail", "--windows-per-day", "9", "--data-dumps-cap-gb", "13"])
    assert script._declared_mismatches(a, t) == [] and a.data_dumps_cap_gb == 13.0
    assert ap.parse_args(["tail-fetch"]).data_dumps_cap_gb == t.DATA_DUMPS_FETCH_CAP_GB == 12.5
    for bad in (["--run-id", "h8_tail_b", "--windows-per-day", "9"], ["--run-id", "h8_tail_b", "--topup-of", "h8_tail"],
                ["--topup-of", "h8_tail"], ["--windows-per-day", "9"]):
        assert script._declared_mismatches(ap.parse_args(["tail-fetch", *bad]), t)
    assert script.main(["tail-fetch", "--run-id", "h8_tail_b", "--root", str(tmp_path / "r")]) == 2
    assert script.main(["tail-fetch", "--run-id", "h8_tail_c", "--topup-of", "h8_tail", "--windows-per-day", "9", "--root", str(tmp_path / "r")]) == 2
    assert ap.parse_args(["tail-seal", "--topup-run", "h8_tail_b"]).topup_run == "h8_tail_b"
    assert script.main(["tail-seal", "--run-id", "h8_tail_b", "--root", str(tmp_path / "r")]) == 2  # b is never sealed on its own


def test_cap_flag_reaches_the_headroom_guard(topup_world, tmp_path):
    w, _ = topup_world
    (tmp_path / "dd").mkdir()
    (tmp_path / "dd" / "big.bin").write_bytes(b"0" * 2_000_000)
    with pytest.raises(t.NotNow):
        run_b(w, data_dumps=tmp_path / "dd", data_dumps_cap_gb=0.001)
    assert run_b(w, data_dumps=tmp_path / "dd", data_dumps_cap_gb=13)["status"] == t.COMPLETE_TOKEN


def test_seal_alone_never_drops_a_pending_top_up_before_t_seal(topup_world):
    w, _ = topup_world
    _h7_done(w)
    kw = dict(seals_dir=w.seals, sleep=lambda s: None, trials_path=w.tmp / "tr.jsonl", wall_clock=lambda: NOW)
    with pytest.raises(t.NotNow, match="pending"):  # not started
        t.seal_tail(w.root, t.RUN_ID, **kw)
    run_b(w, should_stop=lambda: len([1 for k, _ in w.api.log if k == "prices"]) >= 3)
    with pytest.raises(t.NotNow, match="in progress"):  # manifest in progress
        t.seal_tail(w.root, t.RUN_ID, **kw)
    assert not (w.rdir / "SEAL.json").exists() and not (w.root / t.RUN_ID_B / t.NOT_RUN_FILE).exists()


def test_seal_alone_after_t_seal_records_the_real_reason_and_a_separate_refusal_reason(topup_world):
    w, _ = topup_world
    _h7_done(w)
    late = lambda: t.T_SEAL_EPOCH + 1  # noqa: E731
    kw = dict(seals_dir=w.seals, sleep=lambda s: None, trials_path=w.tmp / "tr.jsonl", wall_clock=late)
    res = t.seal_tail(w.root, t.RUN_ID, **kw)  # never started: no manifest
    assert res["topup"] == {"run_id": "h8_tail_b", "status": "dropped", "reason": "never_started_by_T_seal",
                            "refusal_reason": "no_run_left_fetch_refused_or_never_started"}
    seal = json.loads((w.rdir / "SEAL.json").read_text())
    assert seal["declaration"]["topup"]["refusal_reason"] == "no_run_left_fetch_refused_or_never_started"
    assert "topup_frame_disclosure" not in seal["declaration"]


def test_seal_alone_after_t_seal_incomplete_b_is_not_run_deadline_with_no_refusal(tmp_path):
    w = World(tmp_path)
    assert w.run()["status"] == t.COMPLETE_TOKEN
    run_b(w, should_stop=lambda: len([1 for k, _ in w.api.log if k == "prices"]) >= 3)
    _h7_done(w)
    res = t.seal_tail(w.root, t.RUN_ID, seals_dir=w.seals, sleep=lambda s: None, trials_path=tmp_path / "tr.jsonl",
                      wall_clock=lambda: t.T_SEAL_EPOCH + 1)
    assert res["topup"] == {"run_id": "h8_tail_b", "status": "dropped", "reason": t.NOT_RUN_TOKEN, "refusal_reason": "none"}


def test_union_seal_declares_the_frame_state_after_t_fetch8(topup_world, tmp_path):
    w, _ = topup_world
    kw = _union_ready(w, tmp_path)
    t.seal_tail(w.root, t.RUN_ID, topup_run_id=t.RUN_ID_B, **kw)
    decl = json.loads((w.rdir / "SEAL.json").read_text())["declaration"]
    assert "after T_fetch8" in decl["topup_frame_disclosure"] and "end dates" in decl["topup_frame_disclosure"]
