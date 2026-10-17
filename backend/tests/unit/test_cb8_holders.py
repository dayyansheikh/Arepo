# ruff: noqa: E501
"""CB8-H collection: frame, sample, /holders parsing, concentration, smoke, daily snapshot (start gate, resume, failures, disk budget, missed
days, completion), windowed prints with the storage rule, capture marks, and the run_cb8 CLI guards. Mocked HTTP only."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from astrolabe.research_lab import cb8_common as cm
from astrolabe.research_lab import cb8_holders as h
from astrolabe.research_lab import history_backfill as hb
from tests.unit._cb8_fakes import (
    HOUR,
    RAW_PREFIX,
    T0,
    Api,
    Clock,
    all_bytes,
    cap_row,
    capture,
    fingerprint_and_sha,
    holder_groups,
    make_key,
    nosleep,
    print_row,
    write_smoke,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import run_cb8 as script  # noqa: E402


def read_csv(path: Path) -> list[dict]:
    return list(h._read_gz_csv(path))


class Env:
    def __init__(self, tmp_path: Path):
        self.tmp = tmp_path
        self.key_path = make_key(tmp_path)
        self.key = cm.load_wallet_key_strict(self.key_path)
        self.sha, self.fp = fingerprint_and_sha("holders", self.key)
        self.root = tmp_path / "holders"
        self.smoke = tmp_path / "holders_smoke.json"
        write_smoke(self.smoke, self.sha, self.fp)
        self.api = Api()
        self.clock = Clock(T0)
        rows = [cap_row(i) for i in range(12)] + [cap_row(i, sports=True) for i in range(12, 18)]
        rows += [cap_row(18, updown=True), cap_row(19, accepting="0"), cap_row(20, oi=500.0)]
        self.rows = rows
        for r in rows:
            self.api.holders[r["condition_id"]] = holder_groups(r["condition_id"])
        self.caps: list[dict] = []

    def add_capture(self, name: str, start: float, finish: float | None = None) -> dict:
        c = capture(self.tmp / "caps" / name, start, finish if finish is not None else start + 600, self.rows, cid=name)
        self.caps.append(c)
        return c

    def snap(self, **kw):
        args = dict(key=self.key, fp=self.fp, rules_sha=self.sha, smoke_path=self.smoke, captures_fn=lambda: list(self.caps), n_main=8, n_sports=3,
                    wall_clock=self.clock, sleep=nosleep, rps=100.0)
        args.update(kw)
        return h.holders_snap(self.root, self.api, **args)

    def prints(self, **kw):
        args = dict(key=self.key, fp=self.fp, rules_sha=self.sha, smoke_path=self.smoke, captures_fn=lambda: list(self.caps), wall_clock=self.clock,
                    sleep=nosleep, rps=100.0)
        args.update(kw)
        return h.holders_prints(self.root, self.api, **args)


@pytest.fixture
def env(tmp_path):
    return Env(tmp_path)


# ---- frame, sample, parsing -----------------------------------------------------------------------------------------------------------------


def test_frame_filters_and_counts(env):
    cap = env.add_capture("c1", T0)
    frame, counts = h.holders_frame(h.read_capture(cap["dir"]))
    assert counts["n_frame"] == 18
    assert counts["dropped"] == {"crypto_updown": 1, "not_accepting_orders": 1, "open_interest_below_min": 1}
    assert sum(1 for r in frame if r["group"] == "sports") == 6
    assert h.holders_frame([{"market_id": "x", "accepting_orders": None}])[1]["dropped"] == {"no_sidecar_row": 1}


def test_sample_is_deterministic_stratified_and_day_seeded(env):
    cap = env.add_capture("c1", T0)
    frame, _ = h.holders_frame(h.read_capture(cap["dir"]))
    s1, rep = h.holders_sample(frame, "2026-10-21", 8, 3)
    s2, _ = h.holders_sample(frame, "2026-10-21", 8, 3)
    s3, _ = h.holders_sample(frame, "2026-10-22", 8, 3)
    assert [r["market_id"] for r in s1] == [r["market_id"] for r in s2]
    assert sorted(r["market_id"] for r in s1) != sorted(r["market_id"] for r in s3)
    assert sum(r["group"] == "main" for r in s1) == 8 and sum(r["group"] == "sports" for r in s1) == 3
    assert rep["seed"] == "arepo-cb8-holders-2026-10-21" and {r["stratum"].split("|")[1] for r in s1} == {"t0", "t1", "t2"}
    allr, _ = h.holders_sample(frame, "2026-10-21", 100, 100)  # fewer markets than requested: take all
    assert len(allr) == 18


def test_parse_holders_ranks_hashes_and_flags_shape(env):
    rows, info = h.parse_holders(holder_groups("c1", n=3), env.key)
    assert info["shape_ok"] and info["max_rows_token"] == 3 and info["n_tokens"] == 2
    t0 = [r for r in rows if r[0] == 0]
    assert [r[1] for r in t0] == [1, 2, 3] and t0[0][3] > t0[1][3] and all(len(r[2]) == 32 for r in rows)
    assert RAW_PREFIX not in json.dumps(rows)
    bad = [{"token": "t", "holders": [{"proxyWallet": "", "amount": 1, "outcomeIndex": 0}, {"proxyWallet": "0xa", "amount": -3, "outcomeIndex": 0},
                                      {"proxyWallet": "0xb", "amount": "x", "outcomeIndex": 7}]}]
    _, info = h.parse_holders(bad, env.key)
    assert not info["shape_ok"] and info["blank_wallet"] == 1 and info["malformed"] == 2
    assert not h.parse_holders({"holders": []}, env.key)[1]["shape_ok"]
    many = [{"token": "t", "holders": [{"proxyWallet": f"0x{i}", "amount": i, "outcomeIndex": 0} for i in range(30)]}]
    r30, i30 = h.parse_holders(many, env.key)
    assert len(r30) == 20 and i30["max_rows_token"] == 30 and r30[0][3] == 29


def test_concentration_formula_and_oi_flag():
    rows = [[0, 1, "a", 600.0], [0, 2, "b", 300.0], [1, 1, "c", 50.0]]
    c = h.concentration(rows, 2000.0)
    assert c["c0"] == pytest.approx(0.3) and c["c1"] == pytest.approx(0.025) and c["oi_below_sum"] == 0
    c = h.concentration(rows, 500.0)  # OI below the top-20 sum: the denominator is the sum (conservative), flagged
    assert c["c0"] == pytest.approx(600 / 900) and c["oi_below_sum"] == 1
    assert h.concentration([[0, 1, "a", 5.0]], 1.0)["c0"] == 1.0
    assert h.concentration([], 10.0)["c0"] != h.concentration([], 10.0)["c0"]  # NaN: no rows, no concentration


# ---- smoke ----------------------------------------------------------------------------------------------------------------------------------------


def smoke_env(env, n=24):
    rows = [cap_row(i) for i in range(n)]
    env.rows = rows
    for r in rows:
        env.api.holders[r["condition_id"]] = holder_groups(r["condition_id"])
        env.api.gamma[r["market_id"]] = {"id": r["market_id"], "openInterest": "5100.0"}
    cap = env.add_capture("c1", T0)
    frame, _ = h.holders_frame(h.read_capture(cap["dir"]))
    return frame, cap


def test_smoke_pass_counts_and_ratios_only(env):
    frame, cap = smoke_env(env)
    lim = hb.Limiter(env.api, rps=1000.0, sleep=nosleep)
    res = h.holders_smoke(lim, env.key, frame, env.sha, env.fp, cap["capture_id"])
    assert res["pass"] and res["criterion_a_http_ok"] and res["criterion_b_shape"] and res["criterion_c_rows_per_token_le_20"]
    assert res["n_requested"] == 20 and res["n_http_ok"] == 20 and res["criterion_e_oi_units_label"] == "units consistent"
    assert len(res["oi_ratios"]) == 20 and res["oi_ratios"][0]["gamma_oi_over_capture_oi"] == pytest.approx(5100 / 5000, rel=0.01)
    text = json.dumps(res)
    assert RAW_PREFIX not in text and "market_id" not in text and "wallet_hash" not in text


def test_smoke_units_unverified_and_fails(env):
    frame, cap = smoke_env(env)
    for r in env.rows:  # holders hold far more than the open interest
        env.api.holders[r["condition_id"]] = holder_groups(r["condition_id"], top=1e6)
    lim = hb.Limiter(env.api, rps=1000.0, sleep=nosleep)
    res = h.holders_smoke(lim, env.key, frame, env.sha, env.fp, cap["capture_id"])
    assert res["criterion_e_oi_units_label"] == "units unverified" and res["pass"]  # the label does not fail the smoke
    frame2 = frame[:10]  # fewer than 20 markets: criteria (a) and (b) fail
    assert not h.holders_smoke(lim, env.key, frame2, env.sha, env.fp, "x")["pass"]
    for cid in list(env.api.holders):  # an HTTP 404/422 on more than one market fails (a)
        env.api.holders[cid] = [{"token": "t"}]
    assert not h.holders_smoke(lim, env.key, frame, env.sha, env.fp, "x")["criterion_b_shape"]


def test_smoke_network_failure_is_not_a_result(env):
    frame, cap = smoke_env(env)
    env.api.fail_all = True
    with pytest.raises(cm.NotNow):
        h.holders_smoke(hb.Limiter(env.api, rps=1000.0, sleep=nosleep), env.key, frame, env.sha, env.fp, "x")


def test_smoke_gate_requires_pass_rules_and_fingerprint(env, tmp_path):
    assert h.smoke_ok(env.smoke, env.sha, env.fp)["pass"]
    with pytest.raises(cm.Refused):
        h.smoke_ok(env.smoke, "0" * 64, env.fp)
    with pytest.raises(cm.Refused):
        h.smoke_ok(env.smoke, env.sha, "1" * 16)
    write_smoke(tmp_path / "fail.json", env.sha, env.fp, ok=False)
    with pytest.raises(cm.Refused, match="FAIL"):
        h.smoke_ok(tmp_path / "fail.json", env.sha, env.fp)
    with pytest.raises(cm.Refused):
        h.smoke_ok(tmp_path / "none.json", env.sha, env.fp)


# ---- the daily snapshot ---------------------------------------------------------------------------------------------------------------------


def test_snap_refuses_before_the_declared_start_with_a_heartbeat(env):
    env.clock.t = datetime(2026, 10, 21, 3, tzinfo=UTC).timestamp()  # before 2026-10-21T06:00Z
    first = env.snap()
    assert first["status"] == "idle_heartbeat" and not env.api.calls  # clean exit 0 resets the queue's tempfail count
    with pytest.raises(cm.NotNow, match="declared start"):
        env.snap()
    env.clock.t = datetime(2026, 10, 21, 7, tzinfo=UTC).timestamp()  # after 06:00 but inside first run + 2 h (03:00 + 2 h = 05:00): start gate is 06:00
    env.add_capture("early", env.clock.t - 600, env.clock.t - 300)
    m = env.snap()  # first capture after the gate is the early one (07:00 - 10 min >= 06:00)
    assert m["status"] == "day_done"


def test_snap_deployment_delay_and_capture_gate(env):
    env.clock.t = T0  # 12:00; first run + 2 h = 14:00 is the declared start
    env.add_capture("before", T0 - 600, T0 - 300)
    assert env.snap()["status"] == "idle_heartbeat"
    env.clock.t = T0 + 1.5 * HOUR
    with pytest.raises(cm.NotNow, match="declared start"):
        env.snap()
    env.clock.t = T0 + 3 * HOUR  # past the gate, but the only capture started before it
    env.caps[-1]["finish"] = env.clock.t - 600
    with pytest.raises(cm.NotNow):
        env.snap()  # idle again (heartbeat sent earlier)
    assert not [c for c in env.api.calls if c[0].endswith("/holders")]


def run_day(env, hours=3.0, name="cap"):
    env.clock.t = T0 + hours * HOUR
    env.add_capture(name, env.clock.t - 1800, env.clock.t - 1200)
    return env.snap()


def test_snap_full_day_files_pins_manifest_and_no_raw_wallet(env):
    env.clock.t = T0
    # first invocation pins the deployment time (T0) so the gate is T0 + 2 h
    assert env.snap()["status"] == "idle_heartbeat"
    m = run_day(env)
    assert m["status"] == "day_done" and m["counts"]["n_ok"] == 11
    day = "2026-10-21"
    snapdir = env.root / "snap"
    plan = h._read_plan(snapdir / f"{day}.plan.json.gz")
    assert plan["seed"] == "arepo-cb8-holders-2026-10-21" and len(plan["markets"]) == 11
    pin = json.loads((snapdir / "t8_h1_start.json").read_text())
    assert pin["t8_h1_start_utc"] == "2026-10-21T14:30:00Z" and pin["h1_end_utc"] == "2026-11-11T14:30:00Z" and pin["collect_max_utc"] == "2026-12-23T14:30:00Z"
    mk = read_csv(snapdir / f"{day}.markets.csv.gz")
    assert len(mk) == 11 and {r["status"] for r in mk} == {"ok"} and all(int(r["h_epoch"]) == int(T0 + 3 * HOUR) for r in mk)
    assert all(r["oi_capture"] and r["capture_id"] == "cap" for r in mk)
    hrows = read_csv(snapdir / f"{day}.holders.csv.gz")
    assert len(hrows) == 11 * 8 and all(len(r["wallet_hash"]) == 32 for r in hrows)
    man = json.loads((snapdir / "manifest.json").read_text())
    assert man["wallet_key_fingerprint"] == env.fp and man["rules_sha256"] == env.sha and man["evidence_role"] == "prospective"
    assert set(man["file_sha256"]) >= {f"{day}.holders.csv.gz", f"{day}.markets.csv.gz", f"{day}.plan.json.gz"}
    assert RAW_PREFIX.encode() not in all_bytes(env.root) and not list(snapdir.glob("*.partial*"))
    n_req = len(env.api.calls)
    with pytest.raises(cm.NotNow, match="already snapshotted"):  # idempotent per UTC day
        env.snap()
    assert len(env.api.calls) == n_req


def test_snap_resumes_after_a_budget_stop_and_requests_once_per_market(env):
    env.clock.t = T0
    env.snap()
    env.clock.t = T0 + 3 * HOUR
    env.add_capture("cap", env.clock.t - 1800, env.clock.t - 1200)
    m = env.snap(budget_min=1e-9)
    assert m["status"] == "in_progress" and m["stopped"] == "budget reached" and not [c for c in env.api.calls if c[0].endswith("/holders")]
    assert (env.root / "snap" / "2026-10-21.plan.json.gz").exists()  # the sample is fixed before the first request
    m = env.snap()
    assert m["status"] == "day_done"
    cids = [c[1]["market"] for c in env.api.calls if c[0].endswith("/holders")]
    assert len(cids) == len(set(cids)) == 11


def test_snap_failed_requests_are_counted_apart_from_no_data(env):
    env.clock.t = T0
    env.snap()
    env.api.fail_holders.add("c0")
    env.api.holders["c1"] = []  # a 200 with no holders is no-data, not a failure
    env.clock.t = T0 + 3 * HOUR
    env.add_capture("cap", env.clock.t - 1800, env.clock.t - 1200)
    statuses = [env.snap(n_main=12, n_sports=6)["status"] for _ in range(3)]
    assert statuses == ["in_progress", "in_progress", "day_done"]
    mk = {r["market_id"]: r for r in read_csv(env.root / "snap" / "2026-10-21.markets.csv.gz")}
    assert mk["m0"]["status"] == "failed" and mk["m1"]["status"] == "empty" and mk["m2"]["status"] == "ok"
    man = json.loads((env.root / "snap" / "manifest.json").read_text())
    assert man["counts"]["n_failed"] == 1 and man["counts"]["n_empty"] == 1 and man["counts"]["request_failures"] == 2


def test_snap_disk_budget_is_a_sticky_end_state(env):
    env.clock.t = T0
    env.snap()
    env.clock.t = T0 + 3 * HOUR
    env.add_capture("cap", env.clock.t - 1800, env.clock.t - 1200)
    m = env.snap(disk_cap=1)
    assert m["status"] == cm.DISK_BUDGET_TOKEN
    calls = len(env.api.calls)
    again = env.snap()
    assert again["status"] == cm.DISK_BUDGET_TOKEN and len(env.api.calls) == calls


def test_snap_refuses_other_fingerprint_and_missing_smoke(env, tmp_path):
    env.clock.t = T0
    env.snap()
    env.clock.t = T0 + 3 * HOUR
    env.add_capture("cap", env.clock.t - 1800, env.clock.t - 1200)
    assert env.snap()["status"] == "day_done"
    env.clock.t += 24 * HOUR
    env.add_capture("cap2", env.clock.t - 1800, env.clock.t - 1200)
    other = "9" * 16
    sha2 = cm.rules_file_doc("holders", other)["rules_sha256"]
    write_smoke(tmp_path / "s2.json", sha2, other)
    with pytest.raises(cm.Refused, match="fingerprint"):  # an existing run never mixes fingerprints
        env.snap(fp=other, rules_sha=sha2, smoke_path=tmp_path / "s2.json")
    with pytest.raises(cm.Refused):
        env.snap(smoke_path=tmp_path / "missing.json")


def test_snap_stale_capture_retry_and_missed_day_marker(env):
    env.clock.t = T0
    env.snap()
    env.clock.t = T0 + 3 * HOUR
    env.add_capture("old", env.clock.t - 6 * HOUR, env.clock.t - 5.9 * HOUR)
    with pytest.raises(cm.NotNow, match="2.5 h"):
        env.snap()
    env.clock.t = datetime(2026, 10, 21, 23, 40, tzinfo=UTC).timestamp()
    env.add_capture("old2", env.clock.t - 7 * HOUR, env.clock.t - 6.9 * HOUR)
    env.add_capture("ok", env.clock.t - 1800, env.clock.t - 1200)
    assert env.snap()["status"] == "day_done"  # fresh capture exists late in the day: still snapshotted
    env.clock.t = T0 + 24 * HOUR * 3 + 3 * HOUR
    env.add_capture("d3", env.clock.t - 1800, env.clock.t - 1200)
    m = env.snap()
    assert m["status"] == "day_done"
    missed = sorted(p.name[:10] for p in (env.root / "snap").glob("*.MISSED.json"))
    assert missed == ["2026-10-22", "2026-10-23"] and m["counts"]["days_missed"] == 2


def test_snap_last_half_hour_without_capture_marks_the_day_missed(env):
    env.clock.t = T0
    env.snap()
    env.clock.t = T0 + 3 * HOUR
    env.add_capture("cap", env.clock.t - 1800, env.clock.t - 1200)
    env.snap()
    env.clock.t = datetime(2026, 10, 22, 23, 45, tzinfo=UTC).timestamp()
    env.add_capture("stale", env.clock.t - 8 * HOUR, env.clock.t - 7.9 * HOUR)
    m = env.snap()
    assert m["status"] == "day_missed" and (env.root / "snap" / "2026-10-22.MISSED.json").exists()


def test_snap_window_pins_completion_and_freeze_slip(env):
    env.clock.t = T0
    env.snap()
    env.clock.t = T0 + 3 * HOUR
    env.add_capture("cap", env.clock.t - 1800, env.clock.t - 1200)
    env.snap()
    start = h.cm.ep("2026-10-21T14:30:00Z")
    with pytest.raises(cm.Refused, match="before T8_H1_end"):
        h.pin_h2(env.root, start + 10 * 86400, now=env.clock.t)
    doc = h.pin_h2(env.root, start + 21 * 86400, now=env.clock.t)
    assert doc["freeze_slip"] is False and doc["t8_h2_end_utc"] == "2026-12-02T14:30:00Z"
    with pytest.raises(cm.Refused, match="write-once|exists"):
        h.pin_h2(env.root, start + 22 * 86400, now=env.clock.t)
    end = h.collection_end(env.root)
    assert end == start + 42 * 86400 + 30 * HOUR
    env.clock.t = end + 60
    m = env.snap()
    assert m["status"] == h.SNAP_COMPLETE and m["complete"] is True
    assert env.snap()["status"] == h.SNAP_COMPLETE  # sticky


def test_freeze_slip_never_extends_collection(env, tmp_path):
    env.clock.t = T0
    env.snap()
    env.clock.t = T0 + 3 * HOUR
    env.add_capture("cap", env.clock.t - 1800, env.clock.t - 1200)
    env.snap()
    start = h.cm.ep("2026-10-21T14:30:00Z")
    doc = h.pin_h2(env.root, start + 50 * 86400, now=env.clock.t)
    assert doc["freeze_slip"] is True
    assert h.collection_end(env.root) == min(start + 63 * 86400, start + 71 * 86400 + 30 * HOUR) == start + 63 * 86400


# ---- prints and marks ----------------------------------------------------------------------------------------------------------------------------


def seed_prints(env):
    hh = int(T0 + 3 * HOUR)
    w1, w2 = f"{RAW_PREFIX}_c3_0_0", f"{RAW_PREFIX}_c3_0_1"
    env.api.trades["c3"] = [print_row("c3", hh + 600, wallet=w1), print_row("c3", hh + 900, wallet="0xstranger1"), print_row("c3", hh + 1200, wallet=w2, size=3.0),
                            print_row("c3", hh + 27 * 3600, wallet=w1)]  # after h + 26 h: outside the window
    # c4: not concentrated; a rank-2 holder trades (top-5 rule stores it), a stranger trades (not stored)
    env.api.trades["c4"] = [print_row("c4", hh + 100, wallet=f"{RAW_PREFIX}_c4_0_1"), print_row("c4", hh + 200, wallet="0xstranger2")]
    # c5: capped (more prints than pages * limit)
    env.api.trades["c5"] = [print_row("c5", hh + i, wallet=f"0xs{i}") for i in range(25)]
    return hh


def collect_day(env, monkeypatch):
    monkeypatch.setattr(h, "PRINT_LIMIT", 10)
    env.api.holders["c3"] = holder_groups("c3", n=2, top=5000.0)  # rank 1 owns 5000 / 7500 of the top-20 sum (OI 5003 is below it): c = 0.67
    env.clock.t = T0
    env.snap()
    env.clock.t = T0 + 3 * HOUR
    cap = env.add_capture("cap", env.clock.t - 1800, env.clock.t - 1200)
    m = env.snap(n_main=12, n_sports=6)
    assert m["status"] == "day_done"
    return seed_prints(env), cap


def test_prints_wait_for_the_lag_then_store_by_rule(env, monkeypatch):
    hh, _ = collect_day(env, monkeypatch)
    env.clock.t = hh + 29 * HOUR
    assert env.prints(day_pages=2)["status"] == "idle_heartbeat"  # first idle call: the clean heartbeat exit
    with pytest.raises(cm.NotNow, match="old enough"):
        env.prints(day_pages=2)
    env.clock.t = hh + 30 * HOUR + 1
    mid = env.add_capture("cap_mid", hh + 10 * HOUR)
    env.add_capture("cap_late", hh + 40 * HOUR)  # beyond h + 30 h: never a mark
    m = env.prints(day_pages=2)
    assert m["status"] == "day_done"
    day = "2026-10-21"
    pr = read_csv(env.root / "prints" / "prints" / f"{day}.csv.gz")
    by_m: dict[str, list[dict]] = {}
    for r in pr:
        by_m.setdefault(r["market_id"], []).append(r)
    assert {r["stored_reason"] for r in by_m["m3"]} == {"all"} and len(by_m["m3"]) == 3  # the print after h + 26 h is out of the window
    assert [r["stored_reason"] for r in by_m["m4"]] == ["top5"] and by_m["m4"][0]["rank"] == "2"
    assert "m5" not in by_m  # capped market-day: unavailable, nothing stored
    assert all(len(r["wallet_hash"]) == 32 for r in pr)
    summ = {r["market_id"]: r for r in read_csv(env.root / "prints" / f"{day}.markets.csv.gz")}
    assert summ["m5"]["status"] == "capped" and summ["m3"]["status"] == "ok" and summ["m3"]["stored_all"] == "1"
    marks = read_csv(env.root / "prints" / "marks" / f"{day}.csv.gz")
    assert {r["capture_id"] for r in marks} == {"cap_mid"} and {r["market_id"] for r in marks} == {"m3", "m4"}
    assert mid["capture_id"] == "cap_mid" and marks[0]["best_bid"] == "0.40"
    assert RAW_PREFIX.encode() not in all_bytes(env.root)
    man = json.loads((env.root / "prints" / "manifest.json").read_text())
    assert man["wallet_key_fingerprint"] == env.fp and f"prints/{day}.csv.gz" in man["file_sha256"]
    with pytest.raises(cm.NotNow):  # nothing else to do
        env.prints(day_pages=2)


def test_prints_failed_market_day_is_counted_apart(env, monkeypatch):
    hh, _ = collect_day(env, monkeypatch)
    env.api.fail_trades.add("c3")
    env.clock.t = hh + 31 * HOUR
    statuses = [env.prints(day_pages=2)["status"] for _ in range(3)]
    assert statuses == ["in_progress", "in_progress", "day_done"]
    summ = {r["market_id"]: r for r in read_csv(env.root / "prints" / "2026-10-21.markets.csv.gz")}
    assert summ["m3"]["status"] == "failed"
    man = json.loads((env.root / "prints" / "manifest.json").read_text())
    assert man["counts"]["n_failed"] == 1 and man["counts"]["request_failures"] == 2


def test_prints_complete_when_snapshot_is_complete_and_all_days_done(env, monkeypatch):
    hh, _ = collect_day(env, monkeypatch)
    env.clock.t = hh + 31 * HOUR
    assert env.prints(day_pages=2)["status"] == "day_done"
    start = h.cm.ep("2026-10-21T14:30:00Z")
    h.pin_h2(env.root, start + 21 * 86400, now=env.clock.t)
    env.clock.t = h.collection_end(env.root) + 60
    assert env.snap()["status"] == h.SNAP_COMPLETE
    m = env.prints(day_pages=2)
    assert m["status"] == h.PRINTS_COMPLETE and m["complete"] is True


def test_capture_marks_window_and_unreadable_capture(tmp_path):
    caps = [capture(tmp_path / "a", 1000.0, 1100.0, [cap_row(1)], "a"), capture(tmp_path / "b", 90000.0, 90100.0, [cap_row(1), cap_row(2)], "b"),
            {"capture_id": "gone", "dir": str(tmp_path / "gone"), "start": 2000.0, "finish": 2100.0}]
    rows, stats = h.capture_marks(caps, {"m1": 900}, window_s=86400.0)
    assert [r[1] for r in rows] == ["a"] and stats["captures_unreadable"] == 1
    rows, _ = h.capture_marks(caps, {"m1": 900, "m2": 80000}, window_s=86400.0)
    assert sorted((r[0], r[1]) for r in rows) == [("m1", "a"), ("m2", "b")]
    assert h.capture_marks(caps, {})[0] == []


# ---- the CLI --------------------------------------------------------------------------------------------------------------------------------------


def test_cli_rules_fingerprint_and_refusals(env, tmp_path, capsys):
    kp = str(env.key_path)
    out = tmp_path / "r.json"
    assert script.main(["rules", "--which", "holders", "--path", str(out), "--wallet-key-path", kp]) == 0
    doc = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert doc["wallet_key_fingerprint"] == env.fp and json.loads(out.read_text())["rules_sha256"] == doc["rules_sha256"]
    assert script.main(["key-fingerprint", "--wallet-key-path", kp]) == 0
    assert script.main(["key-fingerprint", "--wallet-key-path", str(tmp_path / "nokey")]) == 2
    assert not (tmp_path / "nokey").exists()
    common = ["--rules", str(out), "--allow-uncommitted-rules", "--root", str(env.root), "--data-dumps", str(tmp_path), "--disk-cap-gb", "0.1", "--standalone"]
    assert script.main(["holders-snap", *common, "--wallet-key-path", str(tmp_path / "nokey")]) == 2  # missing key: refuse, never create
    assert script.main(["holders-snap", *common, "--wallet-key-path", kp]) == 2  # no smoke result yet
    assert script.main(["holders-snap", *common, "--wallet-key-path", kp, "--n-main", "10"]) == 2  # declared argument changed
    assert script.main(["holders-prints", *common, "--wallet-key-path", kp, "--lag-h", "28"]) == 2
    existing = tmp_path / "smoke_exists.json"
    existing.write_text("{}")
    assert script.main(["holders-smoke", "--rules", str(out), "--allow-uncommitted-rules", "--wallet-key-path", kp, "--out", str(existing), "--standalone"]) == 2
    assert existing.read_text() == "{}"
    other = make_key(tmp_path / "other", content=b"q" * 64)
    assert script.main(["holders-snap", *common, "--wallet-key-path", str(other)]) == 2  # fingerprint mismatch


def test_cli_pin_h2_refuses_without_window_one(tmp_path):
    assert script.main(["holders-pin-h2", "--root", str(tmp_path), "--start-utc", "2026-11-20T00:00:00Z"]) == 2


# ---- review conditions (2026-10-17) -------------------------------------------------------------------------------------------------------------


def first_day(env):
    env.clock.t = T0
    env.snap()
    env.clock.t = T0 + 3 * HOUR
    env.add_capture("cap", env.clock.t - 1800, env.clock.t - 1200)
    assert env.snap()["status"] == "day_done"


def test_window_two_pin_refuses_early_starts_and_records_the_pin_time(env):
    first_day(env)
    start = h.cm.ep("2026-10-21T14:30:00Z")
    h1_end = start + 21 * 86400
    now = h1_end + 5 * HOUR  # window 1 is over; days after it were collected
    with pytest.raises(cm.Refused, match="pin time"):
        h.pin_h2(env.root, now + 1.9 * HOUR, now=now)  # inside pin time + 2 h: onto days already collected
    with pytest.raises(cm.Refused, match="pin time"):
        h.pin_h2(env.root, h1_end, now=now)
    doc = h.pin_h2(env.root, now + 2 * HOUR, now=now)
    assert doc["pinned_epoch"] == now and doc["pinned_utc"] == cm.iso(now) and doc["h2_start_epoch"] == now + 2 * HOUR


def test_unfinished_plan_is_closed_as_incomplete_at_day_end(env):
    env.clock.t = T0
    env.snap()
    env.clock.t = T0 + 3 * HOUR
    env.add_capture("cap", env.clock.t - 1800, env.clock.t - 1200)
    env.snap(budget_min=1e-9)  # plan written, nothing requested
    env.api.fail_holders.update({f"c{i}" for i in range(6, 12)})
    env.snap()  # a partial day: some markets done, some failing (attempts left)
    rdir = env.root / "snap"
    assert (rdir / "2026-10-21.plan.json.gz").exists() and (rdir / "2026-10-21.partial.jsonl.gz").exists()
    env.clock.t = T0 + 24 * HOUR + 3 * HOUR
    env.add_capture("cap2", env.clock.t - 1800, env.clock.t - 1200)
    m = env.snap()
    marker = json.loads((rdir / "2026-10-21.INCOMPLETE.json").read_text())
    assert marker["reason"] == "incomplete at day end" and marker["n_planned"] == 11 and 0 < marker["n_done"] < 11
    assert (rdir / "2026-10-21.markets.csv.gz").exists() and not (rdir / "2026-10-21.partial.jsonl.gz").exists() and not (rdir / "2026-10-21.fail.jsonl").exists()
    assert len(read_csv(rdir / "2026-10-21.markets.csv.gz")) == marker["n_done"]
    assert m["counts"]["days_incomplete"] == 1 and m["day"] == "2026-10-22"


def test_marks_record_the_expected_window_and_the_earliest_available_capture(env, monkeypatch):
    hh, _ = collect_day(env, monkeypatch)
    env.clock.t = hh + 31 * HOUR
    env.caps[:] = [c for c in env.caps if c["capture_id"] != "cap"]  # the capture of the snapshot itself was removed by retention
    env.add_capture("late_only", hh + 12 * HOUR)
    assert env.prints(day_pages=2)["status"] == "day_done"
    w = json.loads((env.root / "prints" / "marks" / "2026-10-21.window.json").read_text())
    assert w["earliest_capture_available_utc"] == cm.iso(hh + 12 * HOUR) and w["captures_before_earliest_available"] is True
    assert w["window_start_covered"] is False and w["expected_window_utc"] == [cm.iso(hh), cm.iso(hh + 30 * HOUR)] and w["captures_in_window"] == 1
    man = json.loads((env.root / "prints" / "manifest.json").read_text())
    assert "marks/2026-10-21.window.json" in man["file_sha256"]


def test_deep_offset_400_is_capped_but_a_failure_is_not(env, tmp_path):
    api = Api()
    api.max_offset = 10
    base = int(T0)
    api.trades["c1"] = [print_row("c1", base + i) for i in range(40)]
    from astrolabe.research_lab import cb8_common as cmod

    lim = hb.Limiter(api, rps=1000.0, sleep=nosleep)
    rows, info = cmod.windowed_prints(lim, "c1", base, base + 100, 5, env.key, limit=10)
    assert info["capped"] is True and info["offset_cap_status"] == 400 and len(rows) == 20
    api.max_offset = -1  # a 400 on the very first page is a failed request, never "capped"
    with pytest.raises(cmod.ApiError):
        cmod.windowed_prints(lim, "c1", base, base + 100, 5, env.key, limit=10)


def test_smoke_paging_probe_and_q0163_gate(env):
    frame, cap = smoke_env(env)
    lim = hb.Limiter(env.api, rps=1000.0, sleep=nosleep)
    res = h.holders_smoke(lim, env.key, frame, env.sha, env.fp, cap["capture_id"])
    assert res["criterion_g_paging"] is True and res["paging"]["deep_offset"] == "ok"
    env.api.deep_status = 400
    res = h.holders_smoke(lim, env.key, frame, env.sha, env.fp, cap["capture_id"])
    assert res["paging"]["deep_offset"] == "offset_capped" and res["criterion_g_paging"] is True and res["pass"]
    env.api.deep_status = 404
    res = h.holders_smoke(lim, env.key, frame, env.sha, env.fp, cap["capture_id"])
    assert res["paging"]["deep_offset"] == "unexpected" and res["criterion_g_paging"] is False and res["pass"]  # snapshot may run; prints may not
    env.api.deep_status = 500  # a failure is not a capped window: the smoke is not a result at all
    with pytest.raises(cm.NotNow):
        h.holders_smoke(lim, env.key, frame, env.sha, env.fp, cap["capture_id"])


def test_q0163_refuses_without_the_paging_criterion(env, tmp_path):
    write_smoke(env.smoke, env.sha, env.fp, paging=False)
    assert h.smoke_ok(env.smoke, env.sha, env.fp)["pass"]
    with pytest.raises(cm.Refused, match="paging"):
        env.prints()


def test_long_waits_return_distinct_heartbeats_instead_of_tempfails(env):
    env.clock.t = T0
    env.snap()
    env.clock.t = T0 + 11 * HOUR
    env.add_capture("old", env.clock.t - 6 * HOUR, env.clock.t - 5.9 * HOUR)
    first = env.snap()
    assert first["status"] == "idle_heartbeat" and first["idle_kind"] == "no_fresh_capture" and first["complete"] is False
    with pytest.raises(cm.NotNow):
        env.snap()
    env.clock.t += cm.HEARTBEAT_S
    env.add_capture("old2", env.clock.t - 6 * HOUR, env.clock.t - 5.9 * HOUR)
    assert env.snap()["idle_kind"] == "no_fresh_capture"
    env.clock.t += cm.HEARTBEAT_S
    full = env.snap(data_dumps=env.tmp, data_dumps_cap_gb=0.0)  # no headroom
    assert full["status"] == "idle_heartbeat" and full["idle_kind"] == "headroom"
    assert json.loads((env.root / "snap" / "heartbeat.json").read_text())["idle_kind"] == "headroom"
    pr = env.prints(data_dumps=env.tmp, data_dumps_cap_gb=0.0)
    assert pr["idle_kind"] == "headroom"


def test_cli_disk_caps_must_match_the_declaration(env, tmp_path):
    kp = str(env.key_path)
    out = tmp_path / "r.json"
    assert script.main(["rules", "--which", "holders", "--path", str(out), "--wallet-key-path", kp]) == 0
    base = ["--rules", str(out), "--allow-uncommitted-rules", "--root", str(env.root), "--data-dumps", str(tmp_path), "--standalone", "--wallet-key-path", kp]
    assert (h.SNAP_OUTPUT_CAP_GB, h.PRINTS_OUTPUT_CAP_GB) == (0.15, 0.12)
    # a cap other than the declared one is refused before anything else (exit 2); the declared one passes that check (and then stops at the missing smoke, exit 2 too)
    assert script.main(["holders-snap", *base, "--disk-cap-gb", "0.10"]) == 2
    assert script.main(["holders-prints", *base, "--disk-cap-gb", "0.15"]) == 2
