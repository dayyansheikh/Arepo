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
        self.clock = Clock(T0, tick=0.001)
        rows = [cap_row(i) for i in range(12)] + [cap_row(i, sports=True) for i in range(12, 18)]
        rows += [cap_row(18, updown=True), cap_row(19, accepting="0"), cap_row(20, oi=500.0)]
        self.rows = rows
        for r in rows:
            self.api.holders[r["condition_id"]] = holder_groups(r["condition_id"])
            self.api.oi[r["condition_id"]] = float(r["open_interest"])
        self.caps: list[dict] = []

    def add_capture(self, name: str, start: float, finish: float | None = None) -> dict:
        c = capture(self.tmp / "caps" / name, start, finish if finish is not None else start + 600, self.rows, cid=name)
        self.caps.append(c)
        return c

    def snap(self, **kw):
        args = dict(key=self.key, fp=self.fp, rules_sha=self.sha, smoke_path=self.smoke, captures_fn=lambda: list(self.caps), n_main=8, n_sports=3,
                    wall_clock=self.clock, sleep=nosleep, rps=100.0, oi_rps=100.0)
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


def build_frame(env, cap, **kw):
    """(base, frame, summary, done) with the /oi frame fetched from the fake API."""
    base, _ = h.holders_frame(h.read_capture(cap["dir"]))
    lim = hb.Limiter(env.api, rps=1000.0, sleep=nosleep)
    batches = h.oi_batches(base)
    done: dict[int, dict] = {}
    h.run_oi_batches(lim, batches, env.clock, done, **kw)
    states = h.oi_states(batches, done)
    frame, _ = h.apply_oi(base, states)
    return base, frame, h.oi_summary(base, states, batches, done), done


def test_frame_filters_and_counts(env):
    cap = env.add_capture("c1", T0)
    base, counts = h.holders_frame(h.read_capture(cap["dir"]))
    assert counts["n_base"] == 19 and len(base) == 19  # no OI filter in the base frame (OI comes from /oi at t_f)
    assert counts["dropped"] == {"crypto_updown": 1, "not_accepting_orders": 1}
    assert h.holders_frame([{"market_id": "x", "accepting_orders": None}])[1]["dropped"] == {"no_sidecar_row": 1}
    _, frame, summ, _ = build_frame(env, cap)
    assert len(frame) == 18 and sum(1 for r in frame if r["group"] == "sports") == 6  # the OI 500 market is dropped by the >= 1,000 threshold
    assert summ["states"] == {"ok": 19, "oi_lookup_failed": 0, "oi_absent": 0, "oi_nonnumeric": 0} and summ["n_missing"] == 0
    assert all(r["oi_t_f"] > 0 and r["oi"] >= h.MIN_OI for r in frame)


def test_sample_is_deterministic_stratified_and_day_seeded(env):
    cap = env.add_capture("c1", T0)
    _, frame, _, _ = build_frame(env, cap)
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


def smoke_env(env, n=24, single=12):
    """``n`` base markets; the first ``single`` are single-market events whose event OI equals the /oi value."""
    rows = [cap_row(i) for i in range(n)]
    for i, r in enumerate(rows):
        if i < single:
            r["event_id"], r["event_open_interest"] = f"solo{i}", r["open_interest"]
    env.rows = rows
    for r in rows:
        env.api.holders[r["condition_id"]] = holder_groups(r["condition_id"])
        env.api.oi[r["condition_id"]] = float(r["open_interest"])
    cap = env.add_capture("c1", T0)
    base, _ = h.holders_frame(h.read_capture(cap["dir"]))
    return base, cap


def run_smoke(env, base, cap, **kw):
    lim = hb.Limiter(env.api, rps=1000.0, sleep=nosleep)
    return h.holders_smoke(lim, env.key, base, env.sha, env.fp, cap["capture_id"], clock=kw.pop("clock", env.clock), oi_rps=100.0, **kw)


def test_smoke_pass_counts_and_ratios_only(env):
    base, cap = smoke_env(env)
    res = run_smoke(env, base, cap)
    assert res["smoke_version"] == "cb8-holders-smoke-v3" and res["v1_record"]["result"] == "FAIL" and res["v2_record"]["criteria_failed"] == ["h"]
    assert res["pass"] and res["criterion_a_http_ok"] and res["criterion_b_shape"] and res["criterion_c_rows_per_token_le_20"]
    assert res["criterion_h_oi_source"] and res["n_requested"] == 20 and res["n_http_ok"] == 20 and res["criterion_e_oi_units_label"] == "units consistent"
    assert len(res["oi_ratios"]) == 20
    solo = [x for x in res["oi_ratios"] if x["event_oi_single_market"] is not None]
    assert solo and all(x["oi_tf_over_event_oi"] == pytest.approx(1.0) for x in solo)
    assert all(x["sum_top20_over_oi_tf"] is not None for x in res["oi_ratios"]) and "n_gamma_lookup_failed" not in res
    assert res["event_oi_comparison"]["n_agree"] == res["event_oi_comparison"]["n_single_market_events_in_frame"] == 12
    assert res["t_f_asserted_before_first_holders_request"] and res["first_holders_request_epoch"] > res["oi"]["t_f_max_epoch"]
    g = res["sample_disclosure"]  # realised frame and strata against the 1,500 + 300 sample
    assert g["main"]["target"] == 1500 and g["sports"]["target"] == 300 and g["main"]["pool"] == 24 and g["main"]["shortfall"] == 1500 - 24
    assert g["sports"]["pool"] == 0 and g["sports"]["shortfall"] == 300 and sum(g["main"]["strata"].values()) == 24
    assert res["frame_size"] == 24 and "t_f_batches" not in res["oi"]
    text = json.dumps(res)
    assert RAW_PREFIX not in text and "market_id" not in text and "wallet_hash" not in text and "c0" not in res["oi_ratios"][0]


def test_smoke_units_unverified_and_fails(env):
    base, cap = smoke_env(env)
    for r in env.rows:  # holders hold far more than the open interest
        env.api.holders[r["condition_id"]] = holder_groups(r["condition_id"], top=1e6)
    res = run_smoke(env, base, cap)
    assert res["criterion_e_oi_units_label"] == "units unverified" and res["pass"]  # the label does not fail the smoke
    env2 = Env(env.tmp / "y")  # no single-market event: /oi and event OI cannot be compared -> unverified
    base2, cap2 = smoke_env(env2, single=0)
    assert run_smoke(env2, base2, cap2)["criterion_e_oi_units_label"] == "units unverified"
    env3 = Env(env.tmp / "z")
    base3, cap3 = smoke_env(env3)
    for r in env3.rows[:12]:  # event OI in other units (x100): /oi and event OI disagree
        env3.api.oi[r["condition_id"]] = float(r["open_interest"]) / 100.0 + 2000.0
    assert run_smoke(env3, base3, cap3)["criterion_e_oi_units_label"] == "units unverified"
    assert not run_smoke(env, base[:10], cap)["pass"]  # fewer than 20 markets: criteria (a) and (b) fail
    for cid in list(env.api.holders):
        env.api.holders[cid] = [{"token": "t"}]
    assert not run_smoke(env, base, cap)["criterion_b_shape"]


def test_smoke_network_failure_is_not_a_result(env):
    base, cap = smoke_env(env)
    env.api.fail_all = True
    with pytest.raises(cm.NotNow):
        run_smoke(env, base, cap)
    env.api.fail_all = False
    env.api.fail_holders = {r["condition_id"] for r in env.rows}  # /holders unreachable after the /oi frame
    with pytest.raises(cm.NotNow):
        run_smoke(env, base, cap)


def test_absent_contradicted_counts_inside_the_two_percent_rule(env):
    base, cap = smoke_env(env, n=100, single=100)  # every market is a single-market event whose event OI (5000+) is in the capture
    cids = [r["condition_id"] for r in env.rows]
    env.api.oi_absent = set(cids[:2])  # 2 % absent although the capture says event OI >= 1,000: exactly 2 %, not more
    res = run_smoke(env, base, cap)
    assert res["oi"]["n_absent_contradicted"] == 2 and res["oi"]["unavailable_share"] == pytest.approx(0.02) and res["criterion_h_oi_source"]
    env.api.oi_absent = set(cids[:3])
    res = run_smoke(env, base, cap)
    assert res["oi"]["n_absent_contradicted"] == 3 and not res["criterion_h_oi_source"] and not res["pass"] and "unavailable share" in res["oi_source_verdict"]
    # absent markets of multi-market events (event OI blank or event_n > 1) are not contradicted
    base2, cap2 = smoke_env(env, n=100, single=0)
    env.api.oi_absent = set(cids[:60])
    res = run_smoke(env, base2, cap2)
    assert res["oi"]["n_absent_contradicted"] == 0 and res["criterion_h_oi_source"]


def test_snap_day_stops_on_absent_contradicted(env):
    rows = [cap_row(i) for i in range(100)]
    for r in rows:
        r["event_id"], r["event_open_interest"] = f"solo{r['market_id']}", r["open_interest"]
        env.api.holders[r["condition_id"]] = holder_groups(r["condition_id"])
        env.api.oi[r["condition_id"]] = float(r["open_interest"])
    env.rows = rows
    env.api.oi_absent = {r["condition_id"] for r in rows[:3]}
    env.clock.t = T0
    env.snap()
    env.clock.t = T0 + 3 * HOUR
    env.add_capture("cap", env.clock.t - 1800, env.clock.t - 1200)
    m = env.snap()
    assert m["status"] == "day_missed" and m["missed_kind"] == "oi_source"
    marker = json.loads((env.root / "snap" / "2026-10-21.MISSED.json").read_text())
    assert marker["n_absent_contradicted"] == 3 and marker["states"]["oi_absent"] == 3 and marker["unavailable_share"] == pytest.approx(0.03)


def test_absent_probe_picks_highest_volume_and_fails_on_holdings_at_least_min_oi(env):
    base, cap = smoke_env(env, n=100, single=0)
    for r in env.rows:
        r["volume24hr"] = str(int(r["market_id"][1:]))  # m99 has the highest volume
    cap = env.add_capture("c2", T0 + 1)
    base, _ = h.holders_frame(h.read_capture(cap["dir"]))
    cids = {r["market_id"]: r["condition_id"] for r in env.rows}
    absent = [f"m{i}" for i in range(30, 100)]  # 70 absent markets: m80..m99 are the 20 highest-volume ones
    env.api.oi_absent = {cids[m] for m in absent}
    for m in absent:
        env.api.holders[cids[m]] = []
    res = run_smoke(env, base, cap)
    pr = res["absent_probe"]
    assert pr["n_probed"] == 20 and pr["n_absent_in_base"] == 70 and pr["n_no_holders"] == 20 and pr["n_top20_ge_min_oi"] == 0
    assert pr["min_volume24hr_probed"] == 80.0 and res["criterion_i_absent_probe"] and res["pass"]
    probed = {c[1]["market"] for c in env.api.calls if c[0].endswith("/holders") and c[1]["market"] in {cids[m] for m in absent}}
    assert probed == {cids[f"m{i}"] for i in range(80, 100)}
    env.api.holders[cids["m95"]] = holder_groups(cids["m95"], top=2000.0)  # top-20 holdings >= 1,000 on an "absent" market
    res = run_smoke(env, base, cap)
    assert res["absent_probe"]["n_top20_ge_min_oi"] == 1 and res["absent_probe"]["max_top20_sum"] >= 1000 and not res["criterion_i_absent_probe"] and not res["pass"]
    env.api.holders[cids["m95"]] = []
    env.api.holders[cids["m50"]] = holder_groups(cids["m50"], top=2000.0)  # outside the 20 highest-volume absent markets: not probed
    assert run_smoke(env, base, cap)["criterion_i_absent_probe"]


def test_empty_reply_to_a_large_batch_is_split_and_retried(env):
    lim = hb.Limiter(env.api, rps=1000.0, sleep=nosleep)
    ids = [f"z{i}" for i in range(60)]
    states, info = h.fetch_oi_batch(lim, ids)  # nothing listed: an empty 200 for 60 ids (probability about 6e-6 if honest)
    assert [len(x) for x in env.api.oi_requests] == [60, 15, 15, 15, 15] and info["split"] == "empty_reply" and info["n_split_requests"] == 4
    assert all(v == (h.OI_ABSENT, None) for v in states.values()) and len(states) == 60 and not info["integrity_violation"]
    env.api.oi_requests.clear()
    env.api.oi = {"z3": 7.0, "z40": 9.0}  # listed markets: no split
    states, info = h.fetch_oi_batch(lim, ids)
    assert [len(x) for x in env.api.oi_requests] == [60] and "split" not in info and states["z3"] == (h.OI_OK, 7.0)
    env.api.oi_requests.clear()
    env.api.oi = {}
    states, info = h.fetch_oi_batch(lim, ids[:15])  # an empty reply to 15 ids is an honest all-absent batch
    assert [len(x) for x in env.api.oi_requests] == [15] and len(states) == 15 and "split" not in info


def test_403_batch_is_split_into_15s_before_failing(env):
    lim = hb.Limiter(env.api, rps=1000.0, sleep=nosleep)
    ids = [f"z{i}" for i in range(60)]
    env.api.oi = {c: 100.0 + i for i, c in enumerate(ids)}
    env.api.oi_max_ids = 15
    states, info = h.fetch_oi_batch(lim, ids)
    assert info["split"] == "request_failed" and info["n_split_requests"] == 4 and info["http_status"] == 200
    assert all(states[c] == (h.OI_OK, 100.0 + i) for i, c in enumerate(ids))
    assert [len(x) for x in env.api.oi_requests][-4:] == [15, 15, 15, 15] and max(len(x) for x in env.api.oi_requests[:-4]) == 60
    env.api.oi_max_ids = 0  # every request 403s, even single chunks: still a RuntimeError for the caller (network handling)
    with pytest.raises(RuntimeError):
        h.fetch_oi_batch(lim, ids)
    env.api.oi = {}
    base, cap = smoke_env(env, n=100, single=0)  # in the smoke the split is transparent
    env.api.oi_max_ids = 15
    assert run_smoke(env, base, cap)["pass"]


def test_smoke_oi_absent_is_oi_zero_and_the_two_percent_rule_counts_unavailable_only(env):
    base, cap = smoke_env(env, n=100, single=0)
    cids = [r["condition_id"] for r in env.rows]
    env.api.oi_absent = set(cids[:60])  # H-v4: absent = no OI listed = OI 0, excluded by OI >= 1,000, not a source failure
    res = run_smoke(env, base, cap)
    assert res["oi"]["states"]["oi_absent"] == 60 and res["oi"]["missing_share"] == pytest.approx(0.6) and res["oi"]["unavailable_share"] == 0
    assert res["criterion_h_oi_source"] and res["pass"] and res["frame_size"] == 40  # dropped, never imputed or zero-filled
    env.api.oi_absent = set()
    env.api.oi.update({cids[0]: "12.5", cids[1]: None, cids[2]: True})  # 3 % nonnumeric: more than 2 % unavailable
    res = run_smoke(env, base, cap)
    assert not res["criterion_h_oi_source"] and not res["pass"] and "unavailable share" in res["oi_source_verdict"] and res["n_requested"] == 20
    env.api.oi.update({cids[0]: 5000.0, cids[1]: 5000.0})  # one nonnumeric left (1 %): not more than 2 %
    res = run_smoke(env, base, cap)
    assert res["oi"]["states"]["oi_nonnumeric"] == 1 and res["oi"]["unavailable_share"] == pytest.approx(0.01) and res["pass"]
    env.api.oi_absent = set()
    env.api.oi.update({cids[0]: "12.5", cids[1]: None, cids[2]: True, cids[3]: -4.0})
    res = run_smoke(env, base, cap)
    assert res["oi"]["states"]["oi_nonnumeric"] == 4 and not res["pass"]
    env.api.oi = {c: 5000.0 for c in cids}
    env.api.oi_fail_cids = {cids[0]}  # that batch answers 500 on every attempt: the whole batch is oi_lookup_failed? (network -> NotNow in the smoke)
    with pytest.raises(cm.NotNow):
        run_smoke(env, base, cap)
    env.api.oi_fail_cids = set()
    env.api.oi_status = 400  # a server-answered error: every id of the batch is oi_lookup_failed, the smoke FAILs and is written
    res = run_smoke(env, base, cap)
    assert res["oi"]["states"]["oi_lookup_failed"] == 100 and not res["criterion_h_oi_source"] and res["frame_size"] == 0 and not res["pass"]


def test_smoke_t_f_must_precede_the_first_holders_request(env):
    base, cap = smoke_env(env)
    with pytest.raises(cm.Refused, match="t_f ordering"):
        run_smoke(env, base, cap, clock=Clock(T0))  # constant clock: t_f == the first request time, not strictly before
    h.assert_tf_before(10.0, 10.001)
    with pytest.raises(cm.Refused):
        h.assert_tf_before(10.0, 10.0)
    with pytest.raises(cm.Refused):
        h.assert_tf_before(11.0, 10.0)


def test_parse_oi_reply_states_and_batch_assertions():
    sent = ["0xA", "0xb", "0xc", "0xd"]
    ok = lambda rows: h.parse_oi_reply(sent, 200, rows)  # noqa: E731
    st, info = ok([{"market": "0xa", "value": 10.0}, {"market": "0xB", "value": 0}, {"market": "0xc", "value": "7"}])
    assert st["0xA"] == ("ok", 10.0) and st["0xb"] == ("ok", 0.0) and st["0xc"] == ("oi_nonnumeric", None) and st["0xd"] == ("oi_absent", None)
    assert not info["integrity_violation"] and info["n_returned"] == 3
    for bad in (None, True, float("inf"), -1, [1]):
        assert ok([{"market": "0xa", "value": bad}])[0]["0xA"][0] == "oi_nonnumeric"
    for rows in ([{"market": "0xz", "value": 1.0}],  # identity: a returned id that was not sent
                 [{"market": "0xa", "value": 1.0}, {"market": "0xA", "value": 2.0}],  # duplicate
                 [{"market": f"0x{i}", "value": 1.0} for i in range(9)],  # count: more rows than ids sent
                 {"market": "0xa"}):  # not a list
        st, info = ok(rows)
        assert set(st.values()) == {("oi_lookup_failed", None)} and info["integrity_violation"] and len(st) == 4
    st, info = h.parse_oi_reply(sent, 500, None)
    assert set(st.values()) == {("oi_lookup_failed", None)} and not info["integrity_violation"]
    assert h.parse_oi_reply(sent, 400, [])[0]["0xA"][0] == "oi_lookup_failed"


def test_oi_requests_are_batches_of_60_covering_every_base_market_once(env):
    base, cap = smoke_env(env, n=130, single=0)
    build_frame(env, cap)
    sizes = [len(b) for b in env.api.oi_requests]
    assert sizes == [60, 60, 10] and h.OI_BATCH == 60
    sent = [c for b in env.api.oi_requests for c in b]
    assert sorted(sent) == sorted(r["condition_id"] for r in base) and len(set(sent)) == len(sent)
    assert all(u.endswith("/oi") and list(p) == ["market"] for u, p in env.api.calls if u.endswith("/oi"))
    assert h.oi_batches(base) == h.oi_batches(list(reversed(base)))  # deterministic: a resumed build re-forms the same batches


def test_smoke_gate_requires_pass_rules_and_fingerprint(env, tmp_path):
    assert h.smoke_ok(env.smoke, env.sha, env.fp)["pass"]
    v1 = json.loads(env.smoke.read_text()) | {"smoke_version": h.SMOKE_V1_VERSION}  # the v1 result (even a PASS) never opens the gate
    (tmp_path / "v1.json").write_text(json.dumps(v1))
    with pytest.raises(cm.Refused, match="another version"):
        h.smoke_ok(tmp_path / "v1.json", env.sha, env.fp)
    assert h.SMOKE_DEFAULT.name == "holders_smoke_v3.json" and h.SMOKE_V2_PATH.name == "holders_smoke_v2.json" and h.SMOKE_V1_PATH.name == "holders_smoke.json"
    no_h = json.loads(env.smoke.read_text()) | {"criterion_h_oi_source": False}
    (tmp_path / "noh.json").write_text(json.dumps(no_h))
    with pytest.raises(cm.Refused, match="FAIL"):
        h.smoke_ok(tmp_path / "noh.json", env.sha, env.fp)
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
    assert all(r["oi_tf"] and float(r["oi_t_f_epoch"]) < int(r["h_epoch"]) + 1 and r["capture_id"] == "cap" for r in mk)
    assert all(float(r["oi_t_f_epoch"]) < plan["oi"]["t_f_max_epoch"] + 1 for r in mk) and plan["oi"]["t_f_max_epoch"] < min(int(r["h_epoch"]) for r in mk) + 1
    assert plan["frame"]["n_base"] == 19 and plan["frame"]["n_frame"] == 18 and plan["oi"]["states"]["ok"] == 19 and len(plan["oi"]["t_f_batches"]) == 1
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
    assert not (env.root / "snap" / "2026-10-21.plan.json.gz").exists()  # the budget stopped the /oi frame build: no plan, no /holders request
    m = env.snap()
    assert m["status"] == "day_done"
    assert (env.root / "snap" / "2026-10-21.plan.json.gz").exists()  # the sample is fixed before the first /holders request
    cids = [c[1]["market"] for c in env.api.calls if c[0].endswith("/holders")]
    assert len(cids) == len(set(cids)) == 11


def test_snap_oi_frame_resumes_per_batch_with_t_f_per_batch_before_holders(env, monkeypatch):
    rows = [cap_row(i) for i in range(130)]
    env.rows = rows
    for r in rows:
        env.api.holders[r["condition_id"]] = holder_groups(r["condition_id"])
        env.api.oi[r["condition_id"]] = float(r["open_interest"])
    env.clock.t = T0
    env.snap()
    env.clock.t = T0 + 3 * HOUR
    env.add_capture("cap", env.clock.t - 1800, env.clock.t - 1200)
    calls = {"n": 0}

    def stop_after_two(self, should_stop=None):
        calls["n"] += 1
        return "budget reached" if calls["n"] > 2 else None

    monkeypatch.setattr(cm.Cb8Run, "stop_reason", stop_after_two)
    m = env.snap(n_main=20, n_sports=0)
    assert m["status"] == "in_progress" and m["oi_batches_done"] == 2 and m["oi_batches"] == 3
    assert not [c for c in env.api.calls if c[0].endswith("/holders")] and not (env.root / "snap" / "2026-10-21.plan.json.gz").exists()
    assert (env.root / "snap" / "2026-10-21.oi.partial.jsonl.gz").exists() and (env.root / "snap" / "2026-10-21.oi.hdr.json").exists()
    monkeypatch.undo()
    m = env.snap(n_main=20, n_sports=0)
    assert m["status"] == "day_done"
    sent = [c for b in env.api.oi_requests for c in b]
    assert len(sent) == len(set(sent)) == 130  # the two finished batches are not requested again
    plan = h._read_plan(env.root / "snap" / "2026-10-21.plan.json.gz")
    tfs = plan["oi"]["t_f_batches"]
    assert len(tfs) == 3 and tfs == sorted(tfs) and len(set(tfs)) == 3 and plan["oi"]["t_f_max_epoch"] == tfs[-1]
    hs = [int(r["h_epoch"]) for r in read_csv(env.root / "snap" / "2026-10-21.markets.csv.gz")]
    assert min(hs) + 1 > tfs[-1] and len(hs) == 20  # strictly before every /holders request (h is stored in whole seconds)
    assert sorted(p.name for p in (env.root / "snap").glob("*.oi.*")) == []  # transient /oi files are removed
    assert plan["markets"][0]["oi_t_f"] in tfs


def test_snap_oi_source_over_two_percent_stops_the_day_apart_from_a_stale_capture(env):
    rows = [cap_row(i) for i in range(100)]
    env.rows = rows
    for r in rows:
        env.api.holders[r["condition_id"]] = holder_groups(r["condition_id"])
        env.api.oi[r["condition_id"]] = float(r["open_interest"])
    for r in rows[:3]:
        env.api.oi[r["condition_id"]] = "n/a"  # 3 % nonnumeric (H-v4: absent is OI 0 and does not stop a day; unreadable values do)
    env.clock.t = T0
    env.snap()
    env.clock.t = T0 + 3 * HOUR
    env.add_capture("cap", env.clock.t - 1800, env.clock.t - 1200)
    m = env.snap()
    assert m["status"] == "day_missed" and m["missed_kind"] == "oi_source"
    marker = json.loads((env.root / "snap" / "2026-10-21.MISSED.json").read_text())
    assert marker["kind"] == "oi_source" and marker["states"]["oi_nonnumeric"] == 3 and marker["unavailable_share"] == pytest.approx(0.03)
    assert not [c for c in env.api.calls if c[0].endswith("/holders")] and not (env.root / "snap" / "2026-10-21.plan.json.gz").exists()
    assert not list((env.root / "snap").glob("*.oi.*")) and m["counts"]["days_missed_oi_source"] == 1
    with pytest.raises(cm.NotNow, match="already snapshotted"):  # the day stays missed
        env.snap()
    # exactly 2 % is not "more than 2 %": the next day proceeds
    for r in rows[:3]:
        env.api.oi[r["condition_id"]] = float(r["open_interest"])
    env.api.oi_absent = {r["condition_id"] for r in rows[:50]}  # 50 % absent (OI 0): the day proceeds
    env.clock.t += 86400
    env.add_capture("cap2", env.clock.t - 1800, env.clock.t - 1200)
    assert env.snap(n_main=10, n_sports=0)["status"] == "day_done"
    # a stale capture is a different marker
    env.clock.t = datetime(2026, 10, 23, 23, 45, tzinfo=UTC).timestamp()
    m = env.snap()
    assert m["status"] == "day_missed" and m["missed_kind"] == "stale_capture"
    assert json.loads((env.root / "snap" / "2026-10-23.MISSED.json").read_text())["kind"] == "stale_capture"


def test_snap_oi_network_failure_exits_75_keeps_a_resumable_partial_then_gives_up_a_batch(env):
    rows = [cap_row(i) for i in range(130)]
    env.rows = rows
    for r in rows:
        env.api.holders[r["condition_id"]] = holder_groups(r["condition_id"])
        env.api.oi[r["condition_id"]] = float(r["open_interest"])
    env.clock.t = T0
    env.snap()
    env.clock.t = T0 + 3 * HOUR
    env.add_capture("cap", env.clock.t - 1800, env.clock.t - 1200)
    env.api.fail_all = True  # nothing answers: NotNow (exit 75), no manifest status written for the day, no plan
    with pytest.raises(cm.NotNow):
        env.snap()
    assert not (env.root / "snap" / "2026-10-21.plan.json.gz").exists() and not (env.root / "snap" / "2026-10-21.markets.csv.gz").exists()
    env.api.fail_all = False
    bad = sorted(env.api.oi)[0]
    env.api.oi_fail_cids = {bad}  # one batch keeps failing: after 3 attempts its ids are oi_lookup_failed (60 of 130 > 2 %: the day stops)
    for _ in range(3):
        m = env.snap()
        if m.get("status") == "day_missed":
            break
    assert m["status"] == "day_missed" and m["missed_kind"] == "oi_source"
    marker = json.loads((env.root / "snap" / "2026-10-21.MISSED.json").read_text())
    assert marker["states"]["oi_lookup_failed"] == 60 and marker["states"]["ok"] == 70


def test_snap_unfinished_oi_frame_at_day_end_is_missed_oi_source(env, monkeypatch):
    rows = [cap_row(i) for i in range(130)]
    env.rows = rows
    for r in rows:
        env.api.holders[r["condition_id"]] = holder_groups(r["condition_id"])
        env.api.oi[r["condition_id"]] = float(r["open_interest"])
    env.clock.t = T0
    env.snap()
    env.clock.t = T0 + 3 * HOUR
    env.add_capture("cap", env.clock.t - 1800, env.clock.t - 1200)
    monkeypatch.setattr(cm.Cb8Run, "stop_reason", lambda self, should_stop=None: "budget reached")
    assert env.snap()["status"] == "in_progress"
    monkeypatch.undo()
    env.clock.t += 86400
    env.add_capture("cap2", env.clock.t - 1800, env.clock.t - 1200)
    env.snap(n_main=10, n_sports=0)
    marker = json.loads((env.root / "snap" / "2026-10-21.MISSED.json").read_text())
    assert marker["kind"] == "oi_source" and "unfinished" in marker["reason"] and not list((env.root / "snap").glob("2026-10-21.oi.*"))


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


def _late_env(env, n=70):
    rows = [cap_row(i) for i in range(n)]
    env.rows = rows
    for r in rows:
        env.api.holders[r["condition_id"]] = holder_groups(r["condition_id"])
        env.api.oi[r["condition_id"]] = float(r["open_interest"])
    env.clock.t = T0
    env.snap()
    env.clock.t = datetime(2026, 10, 21, 23, 20, tzinfo=UTC).timestamp()
    env.add_capture("late", env.clock.t - 1800, env.clock.t - 1200)


def test_snap_day_rolled_during_the_oi_frame_refuses_the_plan_with_a_sub_reason(env):
    _late_env(env)
    roll = lambda: env.clock() + (3600 if env.api.oi_requests else 0)  # noqa: E731  midnight passes while the /oi frame is built
    m = env.snap(n_main=20, n_sports=0, wall_clock=roll)
    assert m["status"] == "day_missed" and m["missed_kind"] == "oi_source" and m["sub_reason"] == "day_rolled"
    marker = json.loads((env.root / "snap" / "2026-10-21.MISSED.json").read_text())
    assert marker["kind"] == "oi_source" and marker["sub_reason"] == "day_rolled"
    assert not (env.root / "snap" / "2026-10-21.plan.json.gz").exists() and not list((env.root / "snap").glob("*.oi.*"))
    assert not [c for c in env.api.calls if c[0].endswith("/holders")]


def test_snap_day_rolled_before_a_holders_request_stops_without_writing_that_day(env):
    _late_env(env)
    plan_p = env.root / "snap" / "2026-10-21.plan.json.gz"
    roll = lambda: env.clock() + (3600 if plan_p.exists() else 0)  # noqa: E731
    m = env.snap(n_main=20, n_sports=0, wall_clock=roll)
    assert m["status"] == "in_progress" and m["stopped"] == "day_rolled"
    assert not [c for c in env.api.calls if c[0].endswith("/holders")] and not (env.root / "snap" / "2026-10-21.markets.csv.gz").exists()


def test_close_oi_days_records_oi_capture_gone_apart_from_unfinished(env):
    _late_env(env, n=130)
    env.caps.clear()
    env.add_capture("late", env.clock.t - 1800, env.clock.t - 1200)
    calls = {"n": 0}

    def stop_after_one(self, should_stop=None):
        calls["n"] += 1
        return "budget reached" if calls["n"] > 1 else None

    import astrolabe.research_lab.cb8_common as _cm

    orig = _cm.Cb8Run.stop_reason
    _cm.Cb8Run.stop_reason = stop_after_one
    try:
        assert env.snap(n_main=20, n_sports=0)["status"] == "in_progress"
    finally:
        _cm.Cb8Run.stop_reason = orig
    env.caps.clear()  # the pinned capture vanished
    try:  # NotNow, or a clean idle heartbeat when the heartbeat interval has passed
        r = env.snap(n_main=20, n_sports=0)
        assert r["idle_kind"] == "oi_capture_gone"
    except cm.NotNow as exc:
        assert "no longer available" in str(exc)
    assert (env.root / "snap" / "2026-10-21.oi.capture_gone.json").exists()
    env.clock.t += 86400
    env.add_capture("next", env.clock.t - 1800, env.clock.t - 1200)
    env.snap(n_main=10, n_sports=0)
    marker = json.loads((env.root / "snap" / "2026-10-21.MISSED.json").read_text())
    assert marker["sub_reason"] == "oi_capture_gone" and not list((env.root / "snap").glob("2026-10-21.oi.*"))
    d = h.declared()["frame"]["oi_source"]
    assert {"day_rolled", "oi_capture_gone"} <= set(d["sub_reasons"]) and "WHOLE batch" in d["drop_granularity"]
