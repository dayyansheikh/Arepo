# ruff: noqa: E501
"""M1 (CH263) code tests: synthetic tmp trees only (never data-dumps). Maps to the frozen text's J1 / J2 / J3 / A rules."""

from __future__ import annotations

import gzip
import json
import math
import shutil
import sys
from pathlib import Path

import pytest
from scipy.stats import beta

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m1_synth as ms  # noqa: E402

from astrolabe.research_lab import m1_analysis as an  # noqa: E402
from astrolabe.research_lab import m1_extract as ex  # noqa: E402
from astrolabe.research_lab import m1_readout as ro  # noqa: E402
from astrolabe.research_lab import m1_spec as sp  # noqa: E402

SPEC = ms.make_spec()
SLOTS = sp.window_slots(SPEC)


def run(store, snap, sweep, now=None, spec=SPEC):
    return ex.run_pass(store, snap, sweep, spec, now=ms.after_end(spec) if now is None else now)


def units_of(store):
    out = []
    for p in sorted((Path(store) / "units").glob("*.jsonl.gz")):
        out += [json.loads(line) for line in gzip.open(p, "rt") if line.strip()]
    return out


@pytest.fixture()
def world(tmp_path):
    snap, sw = ms.build_stores(tmp_path / "src")
    store = tmp_path / "research_lab" / "m1_ch263"
    res = run(store, snap, sw)
    return snap, sw, store, res


def funnel_total(store):
    _i, chain, _l = ex.load_statuses(store)
    tot: dict = {}
    for d in chain:
        for k, v in d.get("funnel", {}).items():
            tot[k] = tot.get(k, 0) + v
    return tot


# --- spec and pins ---------------------------------------------------------------------------------------------------------------------------

def test_window_has_252_slots_and_pins_match_disk():
    assert len(sp.window_slots(sp.SPEC)) == 252
    assert sp.check_pins()["ok"]
    assert sp.spec_sha(SPEC) != sp.spec_sha(sp.SPEC)
    assert len(sp.code_sha()) == 64 and "m1_j0.py" in sp.code_sha_parts()


def test_pin_mismatch_refuses_and_records_values(tmp_path, world):
    snap, sw, _s, _r = world
    tampered = tmp_path / "costs.py"
    tampered.write_text(Path(sp.module_paths()["costs"]).read_text() + "\n# tampered\n")
    paths = sp.module_paths() | {"costs": tampered}
    with pytest.raises(sp.PinMismatch) as e:
        sp.check_pins(SPEC, paths)
    rec = e.value.record
    assert rec["modules"]["costs"]["ok"] is False and rec["modules"]["costs"]["actual"] != rec["modules"]["costs"]["expected"]
    assert rec["modules"]["calibration"]["ok"] is True
    with pytest.raises(sp.PinMismatch):
        ex.run_pass(tmp_path / "x" / "research_lab" / "m1_ch263", snap, sw, SPEC, now=ms.after_end(SPEC), paths=paths)
    bad_design = tmp_path / "d.md"
    bad_design.write_text("changed")
    with pytest.raises(sp.PinMismatch) as e2:
        sp.check_pins(SPEC, None, bad_design)
    assert e2.value.record["design"]["ok"] is False


# --- J1: eligibility classes ----------------------------------------------------------------------------------------------------------------

def test_units_and_each_eligibility_class(world):
    _snap, _sw, store, res = world
    us = units_of(store)
    assert sorted(u["market_id"] for u in us) == [1, 2, 9, 10]
    f = funnel_total(store)
    assert f["unit"] == 4
    assert f["out_of_scope_sports"] == 1 and f["contested"] == 1 and f["disputed_at_k"] == 1 and f["not_two_sided"] == 1
    assert f["prior_proposal_state"] == 1 and f["no_k_minus_1_row"] == 1 and f["not_open_at_k"] == 1
    assert f["no_previous_capture"] >= 2 and f["already_proposed"] > 0  # first window capture and the capture after the missing slot
    assert res["missing_capture"] == 1 and res["processed"] == ms.W - 1
    by = {u["market_id"]: u for u in us}
    assert by[1]["side"] == "YES" and by[1]["ladder"] == "standalone" and by[1]["tier"] == "10k-100k"
    assert by[2]["side"] == "NO" and by[2]["ask_f"] == 0.98 and by[2]["bid_f"] == 0.96 and by[2]["c"] == 0.02
    assert by[9]["ladder"] == "member_winner" and by[10]["ladder"] == "member_loser" and by[9]["event_open_binary_members"] == 2
    assert all(u["role"] == sp.ROLE and u["spec_sha"] == sp.spec_sha(SPEC) and u["code_sha"] == sp.code_sha() for u in us)
    assert by[1]["status_k"] == '["proposed"]' and by[1]["status_k_minus_1"] == "[]"


def test_prices_rounded_and_fee_lines(world):
    _s, _w, store, _r = world
    by = {u["market_id"]: u for u in units_of(store)}
    u1, u2 = by[1], by[2]
    assert u1["c"] == round(1 - 0.9613, 6) and u1["fee_L1"] == 0.0 and u1["rate_L1"] == 0.0  # fees_enabled false: L1 gives 0
    assert u1["rate_L2"] == 0.04 and u1["fee_L2"] == pytest.approx(0.04 * 0.9613 * (1 - 0.9613))  # L2 ignores the served flag
    assert u2["cat_k"] == "finance" and u2["s2"] == "finance" and u2["rate_L1"] == 0.04
    assert u2["fee_L1"] == pytest.approx(0.04 * 0.98 * 0.02) and u2["fee_L1"] == u2["fee_L2"]
    assert u1["ask_f_at_1"] is False and u1["fee_class"] == "fee_free" and u2["fee_class"] == "fee_on"


def test_sweep_is_descriptor_decision_time_and_caps(world):
    _s, _w, store, _r = world
    by = {u["market_id"]: u for u in units_of(store)}
    assert by[2]["sweep_covered"] and by[2]["sweep_ask_size_1"] == 50 and by[2]["sweep_best_ask"] == 0.98
    assert by[9]["sweep_covered"] and not by[10]["sweep_covered"] and not by[1]["sweep_covered"]
    assert by[2]["t_d"] == by[2]["sweep_batch_receipt_utc"] > by[2]["row_received_utc"]  # latest of row, sidecar, sweep
    assert by[2]["gap_sweep_row_s"] == 360.0 and by[1]["gap_sweep_row_s"] is None and by[1]["t_d"] == by[1]["row_received_utc"]
    assert by[2]["ask_f"] == 0.98  # the price source stays the rows' touch


def test_no_outcome_field_or_future_state_in_units(world):
    _s, _w, store, _r = world
    for p in (store / "units").glob("*.jsonl.gz"):
        assert "YES_WON_SECRET" not in gzip.open(p, "rt").read()
    assert all(u["k_start_ts"] <= u["t_d"] for u in units_of(store))


# --- J1: chronological, missing, late, refusals ------------------------------------------------------------------------------------------

def test_status_chain_and_inputs_hash_sweep(world):
    _s, _w, store, _r = world
    audit = ex.audit_chain(store, SPEC)
    assert audit["ok"] and audit["decided_slots"] == ms.W and audit["missing_slots"] == [ms.slot(ms.MISSING_K)]
    st9 = json.loads((store / "status" / f"{ms.cid(9)}.json").read_text())
    assert any("book_sweeps" in i["path"] and i["sha256"] for i in st9["inputs"])  # sweep-1 files hashed
    assert st9["prev_capture_id"] == ms.cid(8) and st9["state_sha256_before"] != st9["state_sha256_after"] and st9["sweep_1_present"] is True
    prev = json.loads((store / "status" / f"{ms.cid(8)}.json").read_text())
    assert st9["state_sha256_before"] == prev["state_sha256_after"]
    assert (store / "status" / "_init.json").exists()
    init = json.loads((store / "status" / "_init.json").read_text())
    assert init["lookback"]["pre_window_source"] == ms.L


def test_idempotent_rerun_changes_nothing(world):
    snap, sw, store, _r = world
    before = {p: p.read_bytes() for p in store.rglob("*") if p.is_file() and p.name != "j1_runs.jsonl"}
    run(store, snap, sw)
    after = {p: p.read_bytes() for p in store.rglob("*") if p.is_file() and p.name != "j1_runs.jsonl"}
    assert before == after


def test_refuses_overwrite_of_existing_unit_file(tmp_path):
    snap, sw = ms.build_stores(tmp_path / "src")
    store = tmp_path / "research_lab" / "m1_ch263"
    (store / "units").mkdir(parents=True)
    (store / "units" / f"{ms.cid(7)}.jsonl.gz").write_bytes(gzip.compress(b'{"garbage":1}\n'))
    with pytest.raises(ex.M1Refusal, match="overwrite"):
        run(store, snap, sw)


def test_out_of_order_delivery_processes_in_order_with_same_units(tmp_path, world):
    _snap0, _sw0, ref_store, _r = world
    src, sw = ms.build_stores(tmp_path / "all")
    hold = tmp_path / "hold"
    ms.move_capture(src, hold, 8)  # capture 8 is not yet delivered while 9 and later are
    store = tmp_path / "research_lab" / "m1_ch263_x"
    t8 = ms.tcap(8).timestamp()
    r1 = ex.run_pass(store, src, sw, SPEC, now=t8 + 5 * 3600)  # slot 7 is decided (grid + 6 h passed), slot 8 is not: must wait, not skip ahead
    assert r1.get("processed") == 2 and r1.get("waiting_for_slot") == 1  # k = 6, 7 only
    assert not (store / "units" / f"{ms.cid(9)}.jsonl.gz").exists()
    ms.move_capture(hold, src, 8)
    ex.run_pass(store, src, sw, SPEC, now=ms.after_end(SPEC))
    for p in (ref_store / "units").glob("*.jsonl.gz"):
        assert gzip.decompress(p.read_bytes()) == gzip.decompress((store / "units" / p.name).read_bytes())
    assert (store / STATE_FILE).read_bytes() == (ref_store / STATE_FILE).read_bytes()


STATE_FILE = Path("state") / "m1_state.json"


def test_catch_up_equals_live_processing(tmp_path, world):
    _snap, _sw, ref_store, _r = world
    src, sw = ms.build_stores(tmp_path / "live_src", skip=tuple(range(ms.L, ms.L + ms.W)))
    live = tmp_path / "research_lab" / "m1_ch263_live"
    for k in range(ms.L, ms.L + ms.W):  # a pass an hour after each capture arrives, as the live cron does (the missing slot never arrives)
        if k != ms.MISSING_K:
            ms.write_capture(src, k)
        ex.run_pass(live, src, sw, SPEC, now=ms.tcap(k).timestamp() + 3600)
    ex.run_pass(live, src, sw, SPEC, now=ms.after_end(SPEC))
    assert {p.name for p in (ref_store / "units").glob("*")} == {p.name for p in (live / "units").glob("*")}
    for p in (ref_store / "units").glob("*.jsonl.gz"):
        assert gzip.decompress(p.read_bytes()) == gzip.decompress((live / "units" / p.name).read_bytes())
    for p in (ref_store / "status").glob("*.json"):
        a, b = json.loads(p.read_text()), json.loads((live / "status" / p.name).read_text())
        assert a["state_sha256_after"] == b["state_sha256_after"] and a.get("unit_file_sha256") == b.get("unit_file_sha256")


def test_state_holding_a_later_capture_refuses(tmp_path):
    held = tuple(range(ms.L + 4, ms.L + ms.W))
    snap, sw = ms.build_stores(tmp_path / "src", skip=held)
    store = tmp_path / "research_lab" / "m1_ch263"
    ex.run_pass(store, snap, sw, SPEC, now=ms.tcap(ms.L + 3).timestamp() + 6 * 3600 + 1800)  # k = 6, 7, 8, 9 processed
    for k in held:
        if k != ms.MISSING_K:
            ms.write_capture(snap, k)
    st = json.loads((store / STATE_FILE).read_text())
    assert st["last_slot"] == ms.slot(ms.L + 3)
    st["last_slot"] += 2  # a state that already holds a capture at or after the next k
    (store / STATE_FILE).write_text(json.dumps(st))
    with pytest.raises(ex.M1Refusal, match="state chain broken"):
        ex.run_pass(store, snap, sw, SPEC, now=ms.after_end(SPEC))
    st["last_slot"] -= 4  # or a state that lags
    (store / STATE_FILE).write_text(json.dumps(st))
    with pytest.raises(ex.M1Refusal, match="state"):
        ex.run_pass(store, snap, sw, SPEC, now=ms.after_end(SPEC))


def test_broken_chain_is_audited(world):
    _s, _w, store, _r = world
    p = store / "status" / f"{ms.cid(9)}.json"
    d = json.loads(p.read_text())
    d["state_sha256_before"] = "0" * 64
    p.write_text(json.dumps(d))
    a = ex.audit_chain(store, SPEC)
    assert not a["ok"] and any("sha_break" in b for b in a["breaks"])


def test_missing_rule_waits_six_hours_and_late_capture_is_ignored(tmp_path):
    snap, sw = ms.build_stores(tmp_path / "src")
    store = tmp_path / "research_lab" / "m1_ch263"
    g = sp.slot_time(SPEC, ms.slot(ms.MISSING_K))
    r = ex.run_pass(store, snap, sw, SPEC, now=g + 5 * 3600)
    assert r.get("waiting_for_slot") == 1 and "missing_capture" not in r and r["processed"] == ms.MISSING_K - ms.L
    r = ex.run_pass(store, snap, sw, SPEC, now=g + 6 * 3600)
    assert r["missing_capture"] == 1
    ms.write_capture(snap, ms.MISSING_K, finish_after_min=600)  # finishes 10 h after its start, so after grid + 6 h
    r = ex.run_pass(store, snap, sw, SPEC, now=ms.after_end(SPEC))
    assert r["late_capture_ignored"] == 1
    assert not (store / "units" / f"{ms.cid(ms.MISSING_K)}.jsonl.gz").exists()
    assert (store / "status" / f"late_{ms.cid(ms.MISSING_K)}.json").exists()
    assert ex.audit_chain(store, SPEC)["ok"]


# --- J2 -------------------------------------------------------------------------------------------------------------------------------

def test_window_close(world):
    _s, _w, store, _r = world
    with pytest.raises(ex.M1Refusal, match="before END_UTC"):
        ex.close_window(store, SPEC, now=sp.ts(SPEC, "end_utc") + 3600)
    man = ex.close_window(store, SPEC, now=ms.after_end(SPEC))
    assert man["window_slots"] == ms.W and man["processed_slots"] == ms.W - 1 and man["missing_slots"] == [ms.slot(ms.MISSING_K)]
    assert man["units"] == 4 and man["slot_coverage"] == pytest.approx((ms.W - 1) / ms.W) and len(man["manifest_sha256"]) == 64
    assert ex.close_window(store, SPEC, now=ms.after_end(SPEC))["manifest_sha256"] == man["manifest_sha256"]


def test_window_close_refuses_when_slots_undecided(tmp_path):
    snap, sw = ms.build_stores(tmp_path / "src")
    store = tmp_path / "research_lab" / "m1_ch263"
    ex.run_pass(store, snap, sw, SPEC, now=ms.tcap(ms.L + 2).timestamp())
    with pytest.raises(ex.M1Refusal, match="decided"):
        ex.close_window(store, SPEC, now=ms.after_end(SPEC))


# --- J3 -------------------------------------------------------------------------------------------------------------------------------

def mk(mid, uma="resolved", prices='["1","0"]', closed=True, ct="2026-10-21 00:00:00+00"):
    return {"id": str(mid), "umaResolutionStatus": uma, "outcomePrices": prices, "closed": closed, "closedTime": ct}


class FakeGet:
    def __init__(self, closed_recs, open_recs, fail_ids=()):
        self.closed_recs, self.open_recs, self.fail_ids, self.calls = closed_recs, open_recs, set(fail_ids), []

    def __call__(self, params):
        ids = [int(v) for k, v in params if k == "id"]
        closed = ("closed", "true") in params
        self.calls.append((ids, closed))
        if self.fail_ids & set(ids):
            return None, "http_500"
        src = self.closed_recs if closed else self.open_recs
        return [src[i] for i in ids if i in src], "ok"


def closed_world(tmp_path, world):
    _s, _w, store, _r = world
    ex.close_window(store, SPEC, now=ms.after_end(SPEC))
    return store


def test_j3_refuses_before_readout_and_without_manifest(tmp_path, world):
    store = closed_world(tmp_path, world)
    with pytest.raises(ex.M1Refusal, match="before READOUT_UTC"):
        ro.run_j3(store, FakeGet({}, {}), SPEC, now=sp.ts(SPEC, "readout_utc") - 1)
    empty = tmp_path / "e" / "research_lab" / "m1_ch263"
    empty.mkdir(parents=True)
    with pytest.raises(ex.M1Refusal, match="manifest"):
        ro.run_j3(empty, FakeGet({}, {}), SPEC, now=ms.after_readout(SPEC))


def test_j3_coverage_classes_and_retries(tmp_path, world):
    store = closed_world(tmp_path, world)
    g = FakeGet({1: mk(1), 2: mk(2, prices='["0","1"]'), 9: mk(9, prices='["0.5","0.5"]'), 10: mk(10, prices='["0.4","0.4"]')},
                {})  # 1 YES won, 2 NO side won?, 9 split, 10 odd vector; nothing else returned: markets {} not found
    sleeps = []
    t = [sp.ts(SPEC, "readout_utc") + 10.0]

    def clock():
        return t[0]

    def sleep(s):
        sleeps.append(s)
        t[0] += s

    man = ro.run_j3(store, g, SPEC, now=ms.after_readout(SPEC), sleep=sleep, clock=clock)
    rows = {json.loads(line)["market_id"]: json.loads(line) for line in gzip.open(store / "readout" / "readout.jsonl.gz", "rt")}
    assert rows[1]["state"] == "resolved" and rows[1]["y"] == 1 and rows[2]["y"] == 0
    assert rows[9]["state"] == "split_50_50" and rows[10]["state"] == "unavailable_other_price_vector"
    assert man["markets"] == 4 and man["counts"]["resolved"] == 2
    with pytest.raises(ex.M1Refusal, match="overwrite"):
        ro.run_j3(store, g, SPEC, now=ms.after_readout(SPEC), sleep=sleep, clock=clock)
    # not_found and pending are separated by the second pass without `closed`; failures retry 3 times at least an hour apart
    store2 = tmp_path / "w2"
    store2.mkdir()
    shutil.copytree(store, store2 / "s", ignore=shutil.ignore_patterns("readout"))
    g2 = FakeGet({1: mk(1)}, {2: mk(2, uma="proposed", closed=False), 9: mk(9, prices='["1","0"]', ct="")}, fail_ids={10})
    sleeps.clear()
    ro.run_j3(store2 / "s", g2, SPEC, now=ms.after_readout(SPEC), sleep=sleep, clock=clock)
    rows = {json.loads(line)["market_id"]: json.loads(line) for line in gzip.open(store2 / "s" / "readout" / "readout.jsonl.gz", "rt")}
    assert rows[1]["state"] == "resolved" and rows[2]["state"] == "pending"  # 2: no closed record, found without the filter
    assert rows[9]["state"] == "unavailable_fetch" and rows[10]["state"] == "unavailable_fetch"
    assert sum(1 for ids, _c in g2.calls if 10 in ids) == 3 and len(sleeps) == 2 and all(s >= 3500 for s in sleeps)
    nf = FakeGet({}, {})
    store3 = tmp_path / "w3"
    shutil.copytree(store, store3 / "s", ignore=shutil.ignore_patterns("readout"))
    ro.run_j3(store3 / "s", nf, SPEC, now=ms.after_readout(SPEC), sleep=sleep, clock=clock)
    rows = {json.loads(line)["market_id"]: json.loads(line) for line in gzip.open(store3 / "s" / "readout" / "readout.jsonl.gz", "rt")}
    assert {r["state"] for r in rows.values()} == {"not_found"}


# --- A: arithmetic on a hand-computed fixture ---------------------------------------------------------------------------------------------

T_D = 1.7e9


def fx(mid, ev, c, fee1, fee2, side="YES", ask_f=None):
    return {"market_id": mid, "cluster": ev, "side": side, "c": c, "ask_f": 1 - c if ask_f is None else ask_f, "bid_f": 1 - c - 0.01, "mid_f": 1 - c - 0.005, "h": 0.005,
            "fee_L1": fee1, "fee_L2": fee2, "t_d": T_D, "window_day": 1, "ask_f_at_1": False, "tick": 0.001}


def iso_ts(t):
    return sp.iso(t)


def fixture():
    units = [fx(1, "e1", 0.04, 0.001, 0.003), fx(2, "e1", 0.02, 0.0, 0.0), fx(3, "e2", 0.04, 0.002, 0.004), fx(4, "e3", 0.01, 0.0, 0.0, ask_f=0.99),
             fx(5, "e4", 0.03, 0.001, 0.001), fx(6, "e5", 0.05, 0.0, 0.0)]
    ro_ = {1: {"state": "resolved", "y": 1, "closed_time": iso_ts(T_D)},                       # favoured: L = 0, w = 0
           2: {"state": "resolved", "y": 0, "closed_time": iso_ts(T_D)},                       # other side: L = 1
           3: {"state": "split_50_50", "y": None, "closed_time": iso_ts(T_D)},                 # L = 0.5
           4: {"state": "resolved", "y": 1, "closed_time": iso_ts(T_D + 8760 * 3600)},         # w = 8760 h: cap = 0.99 * 0.05
           5: {"state": "pending", "y": None, "closed_time": None, "fetched_utc": iso_ts(T_D)},
           6: {"state": "not_found", "y": None, "fetched_utc": iso_ts(T_D)}}
    return units, ro_


def test_estimand_arithmetic_hand_computed():
    units, rd = fixture()
    notes = an.classify_units(units, rd, SPEC)
    assert [u["cls"] for u in units] == ["resolved_favoured", "resolved_other", "split_50_50", "resolved_favoured", "pending", "not_found"]
    assert notes["wait_upper_bound"] == 2
    final = [u for u in units if u["final"]]
    n = [u["n1"] for u in final]
    assert n == pytest.approx([0.04 - 0 - 0.001, 0.02 - 1, 0.04 - 0.5 - 0.002, 0.01 - 0.0495])
    theta = (0.039 - 0.98 - 0.462 - 0.0395) / 4
    assert sum(n) / 4 == pytest.approx(theta) and theta == pytest.approx(-0.360625)
    h = an.headline(final, SPEC)
    assert h["theta"]["est"] == pytest.approx(theta) and h["theta"]["lo"] <= theta <= h["theta"]["hi"]
    assert h["theta_E"]["est"] == pytest.approx(((0.039 - 0.98) / 2 - 0.462 - 0.0395) / 3)
    assert h["r_eff"]["est"] == pytest.approx((0 + 1 + 0.5 + 0) / 4) and h["P_loss"]["est"] == 0.25 and h["P_split"]["est"] == 0.25
    assert h["c"]["est"] == pytest.approx(0.0275) and h["capital"]["est"] == pytest.approx(0.0495 / 4)
    assert h["theta_L2"]["est"] == pytest.approx((0.04 - 0.003 + 0.02 - 1 + 0.04 - 0.5 - 0.004 + 0.01 - 0.0495) / 4)
    tb = an.tail_bound(final, SPEC)
    p1 = float(beta.ppf(1 - 0.05 / 4, 2, 1))
    assert tb["strata"]["1"]["events"] == 2 and tb["strata"]["1"]["reversed_events"] == 1 and tb["strata"]["1"]["p_upper"] == pytest.approx(p1)
    assert p1 == pytest.approx(math.sqrt(0.9875))
    assert tb["strata"]["2-3"]["p_upper"] == 1.0 and tb["strata"]["4-9"]["events"] == 0
    assert tb["T_U"] == pytest.approx(0.5 * p1 + 0.5 * 1.0)
    assert tb["event_reversal_losses"] == 1 and tb["event_reversal_splits"] == 1 and tb["ten_largest_events"][0] == {"event": "e1", "final_units": 2, "I_e": 1}
    # worst case and not_found as a loss (cap by the 5.2 upper-bound rule: w = 0 here)
    nl = lambda u: u["c"] - 1 - u["fee_L1"]  # noqa: E731
    assert units[4]["n_loss"] == pytest.approx(nl(units[4])) and units[5]["n_loss"] == pytest.approx(0.05 - 1)


def test_ci_is_deterministic_and_event_clustered():
    units, rd = fixture()
    an.classify_units(units, rd, SPEC)
    final = [u for u in units if u["final"]]
    a, b = an.headline(final, SPEC), an.headline(final, SPEC)
    assert a == b
    one = an.event_boot([dict(u, cluster="one") for u in final], {"t": lambda u: u["n1"]}, SPEC)["t"]
    assert one["lo"] == one["hi"] == one["est"]  # one event: every resample is the same
    z = an.event_boot([dict(fx(i, f"e{i}", 0.01, 0, 0), L=0.0) for i in range(5)], {"r": lambda u: u["L"]}, SPEC)["r"]
    assert z["degenerate"] and z["lo"] == z["hi"] == 0.0


# --- A: end to end on the synthetic store ------------------------------------------------------------------------------------------------

def pins_for(store, man):
    return {"spec_sha": sp.spec_sha(SPEC), "code_sha": sp.code_sha(), "manifest_sha256": man["manifest_sha256"],
            "registration_commit_utc": ms.iso(ms.tcap(ms.L) - ms.timedelta(days=3))}


@pytest.fixture()
def full(tmp_path, world):
    store = closed_world(tmp_path, world)
    man = ex.close_window(store, SPEC, now=ms.after_end(SPEC))
    days = {1: mk(1), 2: mk(2, prices='["0","1"]'), 9: mk(9, prices='["0","1"]'), 10: mk(10, prices='["1","0"]')}
    ro.run_j3(store, FakeGet(days, {}), SPEC, now=ms.after_readout(SPEC), sleep=lambda s: None, clock=lambda: sp.ts(SPEC, "readout_utc") + 100.0)
    return store, pins_for(store, man)


def test_analysis_refusals(tmp_path, full):
    store, pins = full
    out = tmp_path / "out.json"
    with pytest.raises(ex.M1Refusal, match="before READOUT_UTC"):
        an.run_analysis(store, pins, out, SPEC, now=sp.ts(SPEC, "readout_utc") + 3600)
    with pytest.raises(ex.M1Refusal, match="requires --out"):
        an.run_analysis(store, pins, None, SPEC, now=ms.after_readout(SPEC))
    with pytest.raises(sp.PinMismatch):
        an.run_analysis(store, pins | {"code_sha": "0" * 64}, out, SPEC, now=ms.after_readout(SPEC))
    with pytest.raises(ex.M1Refusal, match="manifest hash"):
        an.run_analysis(store, pins | {"manifest_sha256": "0" * 64}, out, SPEC, now=ms.after_readout(SPEC))
    out.write_text("x")
    with pytest.raises(ex.M1Refusal, match="overwrite"):
        an.run_analysis(store, pins, out, SPEC, now=ms.after_readout(SPEC))


def test_analysis_end_to_end(tmp_path, full):
    store, pins = full
    res = an.run_analysis(store, pins, tmp_path / "o" / "out.json", SPEC, now=ms.after_readout(SPEC))
    assert (tmp_path / "o" / "out.json").exists() and res["void"] is False
    assert res["eligible_units"] == 4 and res["final_units"] == 4 and res["events"] == 3
    # market 1 YES, y = 1: favoured; market 2 NO side with y = 0 (outcome 0 lost): favoured; 9 YES y = 0: other; 10 NO y = 1: other
    assert res["classes"]["resolved_favoured"] == 2 and res["classes"]["resolved_other"] == 2
    th = res["headline_components"]["theta"]
    assert th["lo"] <= th["est"] <= th["hi"] and f"theta = {th['est']:.6f} [{th['lo']:.6f}, {th['hi']:.6f}]" in res["ledger_line"]  # not a self-comparison
    assert res["coarse"]["coarse"] is True and res["coarse"]["rules_fired"]["1_final_units_below"] is True
    assert res["coverage"]["units"] == 1.0 and res["ask_f_at_1"]["units"] == 0
    assert set(res["splits"]) == {f"S{i}" for i in range(1, 11)}
    assert sum(len(v) for v in res["splits"].values()) == 42  # the declared 42 cells, no unlisted cell
    assert res["splits"]["S6"][">0.10"]["N"] == 0 and res["splits"]["S3"]["standalone"]["N"] == 2
    line = res["ledger_line"]
    assert line.startswith("measured (prospective, k = 0; units seen at a 2 h capture and two-sided at k)")
    assert "theta_low" in line and "theta_W" in line and "covered subset" in line
    assert not an.BANNED.search(json.dumps(res, default=str))
    assert res["capacity"]["covered"] == 2 and "covered subset only" in res["capacity"]["label"]
    # determinism
    res2 = an.run_analysis(store, pins, tmp_path / "o" / "out2.json", SPEC, now=ms.after_readout(SPEC))
    assert (tmp_path / "o" / "out.json").read_bytes() == (tmp_path / "o" / "out2.json").read_bytes() and res2["ledger_line"] == line


def test_analysis_theta_matches_unit_arithmetic(tmp_path, full):
    store, pins = full
    res = an.run_analysis(store, pins, tmp_path / "out.json", SPEC, now=ms.after_readout(SPEC))
    t = res["headline_components"]["theta"]["est"]
    us = {u["market_id"]: u for u in units_of(store)}
    # closedTime 2026-10-21 00:00Z: a wait for the early units, a clock anomaly (w = 0) for the later ones
    ct = sp.ts({"x": "2026-10-21T00:00:00Z"}, "x")

    def cap(u):
        return u["ask_f"] * 0.05 * (max(0.0, ct - u["t_d"]) / 3600.0) / 8760.0

    assert res["wait_notes"].get("wait_clock_anomaly") == sum(1 for u in us.values() if ct < u["t_d"])
    expect = sum(u["c"] - L - u["fee_L1"] - cap(u) for u, L in ((us[1], 0), (us[2], 0), (us[9], 1), (us[10], 1))) / 4
    assert t == pytest.approx(expect)
    assert res["theta_low"] == pytest.approx(res["headline_components"]["c"]["est"] - res["tail_bound"]["T_U"] - res["headline_components"]["fee_L2"]["est"] - res["headline_components"]["capital"]["est"])
    assert res["headline_components"]["capital"]["est"] == pytest.approx(sum(cap(u) for u in us.values()) / 4)


def test_void_on_low_coverage_and_pin_dropping(tmp_path, world):
    store = closed_world(tmp_path, world)
    man = ex.close_window(store, SPEC, now=ms.after_end(SPEC))
    ro.run_j3(store, FakeGet({1: mk(1)}, {}, fail_ids={2, 9, 10}), SPEC, now=ms.after_readout(SPEC), sleep=lambda s: None, clock=lambda: sp.ts(SPEC, "readout_utc") + 5.0)
    res = an.run_analysis(store, pins_for(store, man), tmp_path / "out.json", SPEC, now=ms.after_readout(SPEC))
    assert res["void"] is True and any("11.4" in r for r in res["void_reasons"]) and "ledger_line" not in res and "not_a_measurement" in res
    # unit lines carrying other shas are dropped and counted; above 1% they void
    units, lc = an.load_units(store, pins_for(store, man) | {"spec_sha": "x"})
    assert units == [] and lc["dropped_pin_or_role_mismatch"] == 4


def test_coarse_and_void_flags_are_counts_of_the_frozen_rules():
    co = SPEC["coarse"]
    assert co == {"min_final_units": 2000, "max_ci_half_width_ps": 0.003, "max_tu_ps": 0.003, "max_nonfinal_share": 0.02, "min_slot_coverage": 0.75}
    assert sp.SPEC["coverage_floor"] == 0.95 and sp.SPEC["bootstrap"]["seed"] == 20261124 and sp.SPEC["bootstrap"]["B"] == 10000
    assert sp.SPEC["thin"] == {"final_units": 30, "events": 10}


def test_cell_thin_and_zone_edges():
    units, rd = fixture()
    an.classify_units(units, rd, SPEC)
    row = an.cell_row(units, SPEC)
    assert row["thin"] is True and row["N"] == 6 and row["final"] == 4 and row["nonfinal"] == {"pending": 1, "not_found": 1}
    assert an.split_cell({"c": 0.001000000001}, "S6") == "c<=0.001" and an.split_cell({"c": 0.001001}, "S6") == "(0.001,0.005]"
    assert an.split_cell({"tick": 0.001}, "S9") == "0.001" and an.split_cell({"tick": float("nan")}, "S9") == "other_or_missing"


# --- runner ---------------------------------------------------------------------------------------------------------------------------------

def _runner():
    import importlib.util

    p = Path(__file__).resolve().parents[1] / "scripts" / "run_m1.py"
    spec = importlib.util.spec_from_file_location("run_m1_under_test", p)
    m = importlib.util.module_from_spec(spec)
    sys.modules["run_m1_under_test"] = m
    spec.loader.exec_module(m)
    return m


def test_runner_refusals_and_dry_run(tmp_path, capsys):
    r = _runner()
    assert r.main(["j2", "--store", str(tmp_path / "elsewhere")]) == 2  # wrong store location
    real = tmp_path / "research_lab" / "m1_ch263"
    (tmp_path / "p.json").write_text("{}")
    assert r.main(["analysis", "--store", str(real), "--pins", str(tmp_path / "p.json"), "--out", str(tmp_path / "o.json")]) == 2  # before the real READOUT + 12 h
    assert r.main(["j3", "--store", str(real)]) == 2  # before READOUT_UTC (or no manifest)
    snap, sw = ms.build_stores(tmp_path / "src")
    dry = tmp_path / "research_lab" / "m1_ch263_dryrun"
    assert r.main(["j1", "--store", str(dry), "--snapshot-root", str(snap), "--sweep-root", str(sw), "--dry-run-last-days", "1"]) == 0
    out = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert out["peak_rss_mb"] > 0 and out["processed"] >= 1
    assert r.main(["j1", "--store", str(real), "--snapshot-root", str(snap), "--dry-run-last-days", "1"]) == 2  # a dry run never writes the real store


# --- code-freeze check fixes (reviews/M1_CODE_FREEZE_CHECK_2026-10-30.md): each test fails on the old behaviour ----------------------------------

import csv  # noqa: E402


def rewrite_csv(path, fn):
    with gzip.open(path, "rt", newline="") as fh:
        rows = list(csv.reader(fh))
    rows = fn(rows)
    with gzip.open(path, "wt", newline="") as fh:
        csv.writer(fh).writerows(rows)


def test_must1_missing_rule_reads_manifest_finish_not_run_time(tmp_path, world):
    _s, _w, ref_store, _r = world
    snap, sw = ms.build_stores(tmp_path / "catch_src")
    ms.write_capture(snap, ms.MISSING_K, finish_after_min=600)  # finished 10 h after its start: after grid + 6 h
    store = tmp_path / "research_lab" / "m1_ch263_catch"
    r = run(store, snap, sw)  # a single catch-up run long after the window: live running would have recorded the slot missing
    assert r["missing_capture"] == 1 and r["late_capture_ignored"] == 1 and r["processed"] == ms.W - 1
    assert not (store / "units" / f"{ms.cid(ms.MISSING_K)}.jsonl.gz").exists()
    late = json.loads((store / "status" / f"late_{ms.cid(ms.MISSING_K)}.json").read_text())
    assert late["reason"] == "finished_after_grid_plus_6h"
    for p in (ref_store / "units").glob("*.jsonl.gz"):
        assert gzip.decompress(p.read_bytes()) == gzip.decompress((store / "units" / p.name).read_bytes())
    assert (store / STATE_FILE).read_bytes() == (ref_store / STATE_FILE).read_bytes()
    # the same capture finished on time but delivered late is processed: the rule is a fact about the capture
    snap2, sw2 = ms.build_stores(tmp_path / "ontime_src", skip=())
    r2 = run(tmp_path / "research_lab" / "m1_ch263_ontime", snap2, sw2)
    assert r2["processed"] == ms.W and "missing_capture" not in r2


def test_must2_j1_refuses_before_registered_and_records_noncomplete(tmp_path):
    snap, sw = ms.build_stores(tmp_path / "src")
    d = snap / "partial_before_window"  # a manifest that exists but is not complete, before the window
    d.mkdir()
    (d / "manifest.json").write_text(json.dumps({"state": "running", "started_utc": ms.iso(ms.tcap(2) + ms.timedelta(minutes=20)), "capture_id": "partial"}))
    store = tmp_path / "research_lab" / "m1_ch263"
    with pytest.raises(ex.M1Refusal, match="REGISTERED_UTC"):
        ex.run_pass(store, snap, sw, SPEC, now=sp.ts(SPEC, "registered_utc") - 3 * 86400)
    assert not (store / "state" / "m1_state.json").exists() and not (store / "status" / "_init.json").exists()
    run(store, snap, sw)
    lb = json.loads((store / "status" / "_init.json").read_text())["lookback"]
    assert lb["noncomplete_manifests_before_window"] == 1 and lb["pre_window_source"] == ms.L


def test_must2_q0751_cron_line_notes_the_gate_and_pins():
    q = Path(__file__).resolve().parents[2] / "docs" / "research_lab" / "queue"
    d = json.loads(next(p for p in (q / "jobs" / "q0751_m1_j1.json", q / "drafts" / "q0751_m1_j1.json") if p.exists()).read_text())  # promoted at registration (f939c0b5)
    assert "REGISTERED_UTC" in d["notes"] and "--pins" in d["notes"] and "--pins" in " ".join(d["argv"])


def test_must3_open_record_with_outcome_vector_is_pending():
    assert ro.classify_record(mk(1, closed=False))["state"] == "pending"
    assert ro.classify_record(mk(1, closed="false"))["state"] == "pending"
    assert ro.classify_record(mk(1, closed=True))["state"] == "resolved"
    assert ro.classify_record(mk(1, closed="true"))["state"] == "resolved"


def test_must4_event_is_covered_only_if_every_unit_returned_a_record(tmp_path, world):
    store = closed_world(tmp_path, world)
    man = ex.close_window(store, SPEC, now=ms.after_end(SPEC))
    days = {1: mk(1), 2: mk(2, prices='["0","1"]'), 9: mk(9, prices='["0","1"]')}  # no record for 10, found neither with nor without the closed filter
    ro.run_j3(store, FakeGet(days, {}), SPEC, now=ms.after_readout(SPEC), sleep=lambda s: None, clock=lambda: sp.ts(SPEC, "readout_utc") + 5.0)
    res = an.run_analysis(store, pins_for(store, man), tmp_path / "o.json", SPEC, now=ms.after_readout(SPEC))
    assert res["coverage"]["units"] == pytest.approx(0.75)
    assert res["coverage"]["events_all_units_covered"] == pytest.approx(2 / 3)  # e9 has a unit without a record; the old event-weighted mean was 5/6


def test_must5_registration_commit_is_required_and_void_rule_works(tmp_path, full):
    store, pins = full
    bare = {k: v for k, v in pins.items() if k != "registration_commit_utc"}
    with pytest.raises(ex.M1Refusal, match="registration_commit_utc"):
        an.run_analysis(store, bare, tmp_path / "a.json", SPEC, now=ms.after_readout(SPEC))
    with pytest.raises(ex.M1Refusal, match="registration_commit_utc"):
        an.run_analysis(store, pins | {"registration_commit_utc": "not a time"}, tmp_path / "b.json", SPEC, now=ms.after_readout(SPEC))
    res = an.run_analysis(store, pins | {"registration_commit_utc": sp.iso(sp.ts(SPEC, "registered_utc") - 3600)}, tmp_path / "c.json", SPEC, now=ms.after_readout(SPEC))
    assert res["void"] is True and any("11.6" in r for r in res["void_reasons"])


def test_must6_counted_missingness_reaches_the_output(tmp_path, full):
    store, pins = full
    res = an.run_analysis(store, pins, tmp_path / "o.json", SPEC, now=ms.after_readout(SPEC))
    cc = res["counted_classes"]
    assert cc["j1_status_notes"]["captures_without_sweep_1"] == ms.W - 1 - len(ms.SWEEPS) and cc["missing_capture_slots"] == 1
    assert cc["lookback"]["pre_window_source"] == ms.L and cc["lookback"]["slot_gaps"] == 0 and cc["lookback_notes"] == {}
    assert cc["funnel_sub"] == {"no_previous_capture:first_window_slot": 1} and cc["t_d_fallbacks"] == 0


def test_must6_sidecar_gap_is_counted_once_not_twice(tmp_path):
    snap, sw = ms.build_stores(tmp_path / "src")
    (snap / ms.cid(8) / "rows_ext.csv.gz").unlink()  # capture 8 has no sidecar; it is k - 1 of capture 9 as well
    store = tmp_path / "research_lab" / "m1_ch263"
    run(store, snap, sw)
    cc = an.counted_classes(store)
    assert cc["j1_status_notes"]["captures_without_sidecar"] == 1
    surv = an.survivorship(ex.load_statuses(store)[1])
    assert surv["per_capture"][ms.cid(8)] == "unavailable" and isinstance(surv["per_capture"][ms.cid(9)], dict)
    assert surv["per_day"]["2026-10-20"]["captures_unavailable"] >= 1


def test_must7_missing_row_at_k_and_unparseable_ids_are_counted(tmp_path, monkeypatch):
    monkeypatch.setitem(ms.EXTRA, 13, ("e13", "0.94", "0.96", "politics", "true", 14))
    snap, sw = ms.build_stores(tmp_path / "src")
    rewrite_csv(snap / ms.cid(14) / "rows.csv.gz", lambda rows: [r for r in rows if r[0] != "13"])  # sidecar names 13, the rows do not
    rewrite_csv(snap / ms.cid(9) / "rows.csv.gz", lambda rows: rows + [["abc"] + rows[1][1:]])
    rewrite_csv(snap / ms.cid(9) / "rows_ext.csv.gz", lambda rows: rows + [["xyz"] + rows[1][1:]])
    store = tmp_path / "research_lab" / "m1_ch263"
    run(store, snap, sw)
    f = funnel_total(store)
    assert f["not_open_at_k:no_row_at_k"] == 1 and f["not_open_at_k"] == 1  # market 11's closed row stays not_open_at_k
    cc = an.counted_classes(store)
    assert cc["unparseable_market_id"] == 2 and cc["j1_status_notes"]["unparseable_market_id:rows"] == 1 and cc["j1_status_notes"]["unparseable_market_id:sidecar"] == 1
    assert cc["not_open_at_k_incl_no_row_at_k"] == 2


def test_should1_first_window_slot_sub_count(world):
    _s, _w, store, _r = world
    first = json.loads((store / "status" / f"{ms.cid(ms.L)}.json").read_text())
    assert first["funnel_sub"] == {"no_previous_capture:first_window_slot": first["funnel"]["no_previous_capture"]} and first["funnel"]["no_previous_capture"] > 0
    after_gap = json.loads((store / "status" / f"{ms.cid(ms.MISSING_K + 1)}.json").read_text())
    assert after_gap["funnel_sub"] == {} and after_gap["funnel"]["no_previous_capture"] > 0


def test_should2_l1_flag_parsing_is_conservative():
    f = ex.fees_enabled_tri
    assert f(True, "false") is False and f(True, "0") is False and f(True, "FALSE") is False
    assert f(True, "true") is True and f(True, "1") is True
    assert f(True, "garbage") is None and f(True, "") is None and f(False, "false") is None  # old code: "garbage" -> False (fee 0)


def test_should3_t_d_fallback_is_counted(tmp_path):
    snap, sw = ms.build_stores(tmp_path / "src")
    blank = lambda rows: [rows[0]] + [[r[0], "", *r[2:]] if rows[0][1] == "received_utc" else r for r in rows[1:]]  # noqa: E731
    rewrite_csv(snap / ms.cid(8) / "rows.csv.gz", lambda rows: [rows[0]] + [r[:2] + [""] + r[3:] for r in rows[1:]])
    rewrite_csv(snap / ms.cid(8) / "rows_ext.csv.gz", blank)
    store = tmp_path / "research_lab" / "m1_ch263"
    run(store, snap, sw)
    st = json.loads((store / "status" / f"{ms.cid(8)}.json").read_text())
    us = [u for u in units_of(store) if u["capture_id"] == ms.cid(8)]
    assert us and all(u["t_d_fallback"] and u["t_d"] == u["k_start_ts"] for u in us) and st["t_d_fallbacks"] == len(us)
    assert an.counted_classes(store)["t_d_fallbacks"] == len(us)


def test_should4_unit_without_readout_record_has_its_own_class():
    units, rd = fixture()
    del rd[6]
    notes = an.classify_units(units, rd, SPEC)
    assert units[5]["cls"] == "no_readout_record" and not units[5]["final"] and notes["no_readout_record"] == 1
    assert "no_readout_record" in an.NONFINAL and "no_readout_record" in an.UNCOVERED


def test_should5_duplicate_and_off_grid_captures_are_written_and_counted(tmp_path):
    snap, sw = ms.build_stores(tmp_path / "src")
    for name, minutes in (("dup_of_8", 5), ("off_of_9", 50)):
        src = snap / ms.cid(8 if name.startswith("dup") else 9)
        dst = snap / name
        shutil.copytree(src, dst)
        m = json.loads((dst / "manifest.json").read_text())
        k = 8 if name.startswith("dup") else 9
        m |= {"capture_id": name, "started_utc": ms.iso(ms.tcap(k) + ms.timedelta(minutes=minutes)), "finished_utc": ms.iso(ms.tcap(k) + ms.timedelta(minutes=minutes + 5))}
        (dst / "manifest.json").write_text(json.dumps(m))
    store = tmp_path / "research_lab" / "m1_ch263"
    r = run(store, snap, sw)
    assert r["duplicate_slot_capture_ignored"] == 1 and r["off_grid_capture_ignored"] == 1
    assert (store / "status" / "dup_dup_of_8.json").exists() and (store / "status" / "offgrid_off_of_9.json").exists()
    assert json.loads((store / "status" / "dup_dup_of_8.json").read_text())["kept_capture_id"] == ms.cid(8)
    a = ex.audit_chain(store, SPEC)
    assert a["ok"] and a["duplicate_slot_capture_ignored"] == 1 and a["off_grid_capture_ignored"] == 1
    man = ex.close_window(store, SPEC, now=ms.after_end(SPEC))
    assert man["duplicate_slot_capture_ignored"] == 1 and "status/offgrid_off_of_9.json" in man["files"]


def test_should6_j1_refuses_once_the_window_is_closed(tmp_path, world):
    snap, sw, store, _r = world
    ex.close_window(store, SPEC, now=ms.after_end(SPEC))
    with pytest.raises(ex.M1Refusal, match="window is closed"):
        run(store, snap, sw)


def test_should7_cross_check_compares_final_states_only():
    units = [{"market_id": 1, "cls": "pending", "final": False, "side": "YES"}, {"market_id": 2, "cls": "not_found", "final": False, "side": "YES"},
             {"market_id": 3, "cls": "pending", "final": False, "side": "YES"}, {"market_id": 4, "cls": "split_50_50", "final": True, "side": "YES"},
             {"market_id": 5, "cls": "resolved_favoured", "final": True, "side": "YES"}]
    log = {1: {"state": "not_resolved"}, 2: {"state": "not_found"}, 3: {"state": "resolved", "y": 1}, 4: {"state": "split_50_50"}, 5: {"state": "resolved", "y": 1}}
    cc = an.cross_check(units, log)
    assert cc["agree"] == 4 and cc["disagree"] == 1 and cc["disagreements"][0]["market_id"] == 3  # M1 pending against an engine resolution is a real difference


def test_should8_banned_wording_anywhere_in_the_output_refuses(tmp_path, world):
    store = closed_world(tmp_path, world)
    man = ex.close_window(store, SPEC, now=ms.after_end(SPEC))
    days = {1: mk(1), 2: mk(2, prices='["0","1"]'), 9: mk(9, prices='["0","1"]', uma="confirmed"), 10: mk(10, prices='["1","0"]')}
    ro.run_j3(store, FakeGet(days, {}), SPEC, now=ms.after_readout(SPEC), sleep=lambda s: None, clock=lambda: sp.ts(SPEC, "readout_utc") + 5.0)
    with pytest.raises(ex.M1Refusal, match="banned wording"):  # the word sits in uma_status_by_class, outside the numbers block the old assert scanned
        an.run_analysis(store, pins_for(store, man), tmp_path / "o.json", SPEC, now=ms.after_readout(SPEC))
    assert not (tmp_path / "o.json").exists()


def test_should9_missing_code_file_refuses(tmp_path):
    with pytest.raises(sp.PinMismatch) as e:
        sp.code_sha_parts((*sp.CODE_FILES, tmp_path / "gone.py"))
    assert e.value.record["missing_code_files"] == ["gone.py"]


def test_should10_j1_checks_code_against_the_registered_pins(tmp_path):
    snap, sw = ms.build_stores(tmp_path / "src")
    good = {"spec_sha": sp.spec_sha(SPEC), "code_sha": sp.code_sha()}
    with pytest.raises(sp.PinMismatch):
        ex.run_pass(tmp_path / "research_lab" / "m1_ch263_a", snap, sw, SPEC, now=ms.after_end(SPEC), pins=good | {"code_sha": "0" * 64})
    assert ex.run_pass(tmp_path / "research_lab" / "m1_ch263_b", snap, sw, SPEC, now=ms.after_end(SPEC), pins=good)["processed"] == ms.W - 1
    r = _runner()
    real = tmp_path / "research_lab" / "m1_ch263"
    assert r.main(["j1", "--store", str(real), "--snapshot-root", str(snap)]) == 2  # a real-window pass needs --pins
    (tmp_path / "pins.json").write_text(json.dumps({"spec_sha": "x", "code_sha": "y"}))
    assert r.main(["j1", "--store", str(real), "--snapshot-root", str(snap), "--pins", str(tmp_path / "pins.json")]) == 3  # pins differ from the running code


def test_should11_e4_crypto_and_ask_f_at_1(tmp_path, monkeypatch):
    monkeypatch.setitem(ms.EXTRA, 13, ("e13", "0.94", "0.96", "politics", "false", 14))   # E4: accepting_orders false
    monkeypatch.setitem(ms.EXTRA, 14, ("e14", "0.94", "0.96", "crypto", "true", 14))      # E5: crypto, out of scope
    monkeypatch.setitem(ms.EXTRA, 15, ("e15", "0.98", "1", "politics", "true", 14))       # E6 note: ask_f = 1
    snap, sw = ms.build_stores(tmp_path / "src")
    store = tmp_path / "research_lab" / "m1_ch263"
    run(store, snap, sw)
    f = funnel_total(store)
    assert f["not_open_at_k"] == 2 and f["out_of_scope_crypto"] == 1 and f["unit"] == 5  # 11 (closed) and 13 (not accepting); 14; 15 joins 1, 2, 9, 10
    u15 = [u for u in units_of(store) if u["market_id"] == 15]
    assert len(u15) == 1 and u15[0]["ask_f_at_1"] is True and u15[0]["c"] == 0.0 and u15[0]["side"] == "YES"
    man = ex.close_window(store, SPEC, now=ms.after_end(SPEC))
    days = {1: mk(1), 2: mk(2, prices='["0","1"]'), 9: mk(9, prices='["0","1"]'), 10: mk(10, prices='["1","0"]'), 15: mk(15)}
    ro.run_j3(store, FakeGet(days, {}), SPEC, now=ms.after_readout(SPEC), sleep=lambda s: None, clock=lambda: sp.ts(SPEC, "readout_utc") + 5.0)
    res = an.run_analysis(store, pins_for(store, man), tmp_path / "o.json", SPEC, now=ms.after_readout(SPEC))
    assert res["ask_f_at_1"]["units"] == 1 and res["ask_f_at_1"]["share"] == pytest.approx(0.2)


def test_should12_lookback_slot_gaps_are_counted(tmp_path):
    snap, sw = ms.build_stores(tmp_path / "src", skip=(2, ms.MISSING_K))
    store = tmp_path / "research_lab" / "m1_ch263"
    run(store, snap, sw)
    lb = json.loads((store / "status" / "_init.json").read_text())["lookback"]
    assert lb["pre_window_source"] == ms.L - 1 and lb["slot_gaps"] == 1 and lb["off_grid_captures"] == 0


# --- amendment 18 (docs/research_lab/MEASUREMENT_M1_CH263.md section 18) ---------------------------------------------------------------------

def test_amendment18_m2_overlap_reads_ids_only_and_is_unavailable_without_a_store(tmp_path, full):
    store, pins = full
    res = an.run_analysis(store, pins, tmp_path / "o1.json", SPEC, now=ms.after_readout(SPEC))
    assert res["m2_overlap"] == "unavailable"
    m2 = tmp_path / "research_lab" / "m2_ch264"
    (m2 / "units").mkdir(parents=True)
    lines = [json.dumps({"market_id": 1, "capture_id": ms.cid(8), "ask_f": 0.123457, "class": "SECRETCLASS", "y": 1}, sort_keys=True),
             json.dumps({"market_id": 1, "capture_id": "other_capture", "ask_f": 0.5}), json.dumps({"market_id": 77, "capture_id": ms.cid(9)})]
    (m2 / "units" / "x.jsonl.gz").write_bytes(gzip.compress(("\n".join(lines) + "\n").encode()))
    res2 = an.run_analysis(store, pins, tmp_path / "o2.json", SPEC, now=ms.after_readout(SPEC))
    assert res2["m2_overlap"] == {"count": 1, "m2_unit_ids_read": 3, "m2_lines_missing_a_key": 0, "key": "market_id + capture_id", "pooled": False}
    blob = (tmp_path / "o2.json").read_text()
    assert "0.123457" not in blob and "SECRETCLASS" not in blob  # no M2 price, class or outcome reaches the output
    res3 = an.run_analysis(store, pins, tmp_path / "o3.json", SPEC, now=ms.after_readout(SPEC), m2_store=tmp_path / "nowhere")
    assert res3["m2_overlap"] == "unavailable"


def test_amendment18_survivorship_comes_from_j1_in_scope_sets(tmp_path, full):
    store, pins = full
    st8 = json.loads((store / "status" / f"{ms.cid(8)}.json").read_text())
    ids8 = ex.decode_ids(st8["in_scope_market_ids"])
    assert ids8 == {1, 2, 4, 5, 6, 8, 9, 10, 11, 12} and 3 not in ids8 and st8["in_scope_market_ids"]["n"] == 10  # sports market 3 is out; 7 not yet present
    assert ex.decode_ids(ex.encode_ids({5, 1, 1000003})) == {1, 5, 1000003}
    res = an.run_analysis(store, pins, tmp_path / "o.json", SPEC, now=ms.after_readout(SPEC))
    sv = res["survivorship"]
    assert sv["per_capture"][ms.cid(8)]["in_scope_ids"] == 10 and "cross_check_engine_log" not in res  # no engine log was given
    assert sv["per_day"]["2026-10-20"]["in_scope_ids_distinct"] == 10 and sum(d["m1_units"] for d in sv["per_day"].values()) == res["eligible_units"]
    gone = [dict(d, in_scope_market_ids=None) if d.get("capture_id") == ms.cid(8) else d for d in ex.load_statuses(store)[1]]
    assert an.survivorship(gone)["per_capture"][ms.cid(8)] == "unavailable"


# --- re-check R1-R3, S1-S3 (docs/research_lab/reviews/M1_CODE_RECHECK_2026-10-30.md) ---------------------------------------------------------

def _dup_capture(snap, k, name="A_dup", start_min=-10, fin_min=180):
    A = snap / name
    shutil.copytree(snap / ms.cid(k), A)
    m = json.loads((A / "manifest.json").read_text())
    m.update(capture_id=name, started_utc=ms.iso(ms.tcap(k) + ms.timedelta(minutes=start_min)), finished_utc=ms.iso(ms.tcap(k) + ms.timedelta(minutes=fin_min)))
    (A / "manifest.json").write_text(json.dumps(m))


def test_r1_slot_is_decided_only_after_grid_plus_6h_and_live_equals_catch_up(tmp_path):
    k = ms.L + 2
    snap, sw = ms.build_stores(tmp_path / "src")
    hold = tmp_path / "hold"
    for kk in range(k + 1, ms.L + ms.W):
        if (snap / ms.cid(kk)).exists():
            ms.move_capture(snap, hold, kk)
    store = tmp_path / "research_lab" / "m1_ch263"
    r1 = ex.run_pass(store, snap, sw, SPEC, now=ms.tcap(k).timestamp() + 30 * 60)  # B (start g, finished g + 5 min) is on disk, but the slot is not final
    assert not (store / "status" / f"{ms.cid(k)}.json").exists() and r1.get("waiting_for_slot") == 1
    _dup_capture(snap, k)  # A: same slot, started 10 min earlier, finished g + 3 h (on time)
    ex.run_pass(store, snap, sw, SPEC, now=ms.tcap(k).timestamp() + 4 * 3600)  # still inside the 6 h: no refusal, still waiting
    assert not (store / "status" / f"{ms.cid(k)}.json").exists()
    for kk in range(k + 1, ms.L + ms.W):
        if (hold / ms.cid(kk)).exists():
            ms.move_capture(hold, snap, kk)
    ex.run_pass(store, snap, sw, SPEC, now=ms.after_end(SPEC))
    store2 = tmp_path / "research_lab" / "m1_ch263_catch"
    ex.run_pass(store2, snap, sw, SPEC, now=ms.after_end(SPEC))
    for s_ in (store, store2):  # live and catch-up pick the same capture (A, the earliest start) and fold the same chain
        assert (s_ / "status" / "A_dup.json").exists() and not (s_ / "status" / f"{ms.cid(k)}.json").exists()
    assert (store / STATE_FILE).read_bytes() == (store2 / STATE_FILE).read_bytes()


def test_r1_a_slot_with_any_chain_status_is_not_reprocessed_for_another_capture_id(tmp_path):
    snap, sw = ms.build_stores(tmp_path / "src")
    store = tmp_path / "research_lab" / "m1_ch263"
    run(store, snap, sw)
    before = (store / STATE_FILE).read_bytes()
    _dup_capture(snap, ms.L + 2)  # an earlier-start on-time capture arrives for a slot already decided (e.g. a restart that overlapped)
    run(store, snap, sw)  # must not refuse with "state chain broken"
    assert (store / STATE_FILE).read_bytes() == before and not (store / "status" / "A_dup.json").exists()


def test_must1_late_on_time_capture_never_breaks_the_chain_and_is_recorded_late(tmp_path):
    """Reviewer probe race2: slot k decided with B at grid + 6 h 10 min, then an earlier-start on-time capture A appears."""
    k = ms.L + 2
    snap, sw = ms.build_stores(tmp_path / "src")
    hold = tmp_path / "hold"
    for kk in range(k + 1, ms.L + ms.W):
        if (snap / ms.cid(kk)).exists():
            ms.move_capture(snap, hold, kk)
    store = tmp_path / "research_lab" / "m1_ch263"
    g = ms.tcap(k).timestamp()
    run(store, snap, sw, now=g + 6 * 3600 + 600)
    _dup_capture(snap, k, start_min=-10, fin_min=355)
    for kk in range(k + 1, ms.L + ms.W):
        if (hold / ms.cid(kk)).exists():
            ms.move_capture(hold, snap, kk)
    run(store, snap, sw)  # must not refuse
    late = json.loads((store / "status" / "late_A_dup.json").read_text())
    assert late["kind"] == "late_capture_ignored" and late["reason"] == "on_time_but_delivered_after_slot_decided"
    assert json.loads((store / "status" / f"{ms.cid(k + 1)}.json").read_text())["prev_capture_id"] == ms.cid(k)
    assert not list((store / "status").glob("dup_*.json"))
    assert ex.audit_chain(store, SPEC)["ok"]


def test_must1_duplicate_record_names_the_chain_capture_as_kept(tmp_path):
    """Reviewer probe dup_label: the capture that was processed is the kept one; the later-arriving earlier-start capture is recorded, not lost."""
    k = ms.L + 2
    snap, sw = ms.build_stores(tmp_path / "src")
    store = tmp_path / "research_lab" / "m1_ch263"
    run(store, snap, sw)
    _dup_capture(snap, k, start_min=-10, fin_min=180)
    run(store, snap, sw)
    assert json.loads((store / "status" / "late_A_dup.json").read_text())["reason"] == "on_time_but_delivered_after_slot_decided"
    _dup_capture(snap, k, name="Z_dup", start_min=5, fin_min=180)  # a later-start duplicate: kept is the chain's capture
    run(store, snap, sw)
    assert json.loads((store / "status" / "dup_Z_dup.json").read_text())["kept_capture_id"] == ms.cid(k)


def test_should1_downgraded_record_has_no_outcome():
    out = ro.classify_record({"closed": False, "umaResolutionStatus": "resolved", "outcomePrices": ["1", "0"]})
    assert out["state"] == "pending" and out["parse_reason"] == "not_closed" and out["y"] is None


def test_r2_open_record_with_split_prices_is_pending_not_closed():
    rec = {"id": "1", "closed": False, "umaResolutionStatus": "resolved", "outcomePrices": ["0.5", "0.5"]}
    out = ro.classify_record(rec)
    assert out["state"] == "pending" and out["parse_reason"] == "not_closed" and out["y"] is None
    assert ro.classify_record(rec | {"closed": True})["state"] == "split_50_50"
    assert ro.classify_record({"closed": False, "umaResolutionStatus": "resolved", "outcomePrices": ["1", "0"]})["state"] == "pending"


def test_r3_absent_or_unparseable_finished_utc_is_not_on_time(tmp_path):
    for label, patch in (("absent", None), ("garbage", "not-a-time")):
        snap, sw = ms.build_stores(tmp_path / label / "src", skip=())
        k = ms.L + 3
        mp = snap / ms.cid(k) / "manifest.json"
        m = json.loads(mp.read_text())
        m.pop("finished_utc")
        if patch:
            m["finished_utc"] = patch
        mp.write_text(json.dumps(m))
        store = tmp_path / label / "research_lab" / "m1_ch263"
        r = run(store, snap, sw)
        assert r["late_capture_ignored"] == 1 and r["missing_capture"] >= 1 and not (store / "status" / f"{ms.cid(k)}.json").exists()
        late = json.loads((store / "status" / f"late_{ms.cid(k)}.json").read_text())
        assert late["reason"] == "finished_utc_absent" and late["finished_utc"] is None
        assert (store / "status" / f"missing_{sp.iso(sp.slot_time(SPEC, ms.slot(k))).replace('-', '').replace(':', '')}.json").exists()
        assert an.counted_classes(store)["late_capture_ignored"] == 1


def test_s1_unparseable_manifests_have_their_own_key(tmp_path):
    snap, sw = ms.build_stores(tmp_path / "src")
    bad = snap / "garbled"
    bad.mkdir()
    (bad / "manifest.json").write_text("{not json")
    store = tmp_path / "research_lab" / "m1_ch263"
    run(store, snap, sw)
    lb = json.loads((store / "status" / "_init.json").read_text())["lookback"]
    assert lb["unparseable_manifests"] == 1 and lb["noncomplete_manifests_before_window"] == 0


def test_s2_s3_survivorship_states_the_dropped_clause_and_m2_overlap_counts_keyless_lines(tmp_path, full):
    store, pins = full
    res = an.run_analysis(store, pins, tmp_path / "o1.json", SPEC, now=ms.after_readout(SPEC))
    assert res["survivorship"]["share_seen_before_close"] == "not computed (amendment 18(b))"
    m2 = tmp_path / "research_lab" / "m2_ch264"
    (m2 / "units").mkdir(parents=True)
    lines = [json.dumps({"market_id": 1, "capture_id": ms.cid(8)}), json.dumps({"market_id": 2}), json.dumps({"capture_id": "x"}), json.dumps({"mid": 3, "cap": "y"})]
    (m2 / "units" / "x.jsonl.gz").write_bytes(gzip.compress(("\n".join(lines) + "\n").encode()))
    res2 = an.run_analysis(store, pins, tmp_path / "o2.json", SPEC, now=ms.after_readout(SPEC))
    assert res2["m2_overlap"]["m2_lines_missing_a_key"] == 3 and res2["m2_overlap"]["m2_unit_ids_read"] == 1


def _late_capture(snap, k, name, smin, fmin, src):
    A = snap / name
    shutil.copytree(src, A)
    m = json.loads((A / "manifest.json").read_text())
    m.update(capture_id=name, started_utc=ms.iso(ms.tcap(k) + ms.timedelta(minutes=smin)), finished_utc=ms.iso(ms.tcap(k) + ms.timedelta(minutes=fmin)))
    (A / "manifest.json").write_text(json.dumps(m))


def test_must1b_every_on_time_capture_delivered_after_missing_recorded_is_late(tmp_path):
    """Reviewer probe miss2 (missing): two on-time captures arrive after the slot was recorded missing; both are recorded."""
    k = ms.L + 2
    snap, sw = ms.build_stores(tmp_path / "src")
    hold = tmp_path / "hold"
    ms.move_capture(snap, hold, k)
    store = tmp_path / "research_lab" / "m1_ch263"
    run(store, snap, sw, now=ms.tcap(k).timestamp() + 6 * 3600 + 600)
    _late_capture(snap, k, "X1", 0, 100, hold / ms.cid(k))
    _late_capture(snap, k, "X2", 5, 120, hold / ms.cid(k))
    run(store, snap, sw)
    for n in ("X1", "X2"):
        assert json.loads((store / "status" / f"late_{n}.json").read_text())["reason"] == "delivered_after_missing_recorded"
    assert ex.audit_chain(store, SPEC)["ok"]


def test_should1b_tie_on_start_uses_the_choosers_key(tmp_path):
    """Reviewer probe miss2 (tie): same start, smaller id, arrives after the decision: late (would have been chosen), not dup."""
    k = ms.L + 2
    snap, sw = ms.build_stores(tmp_path / "src")
    store = tmp_path / "research_lab" / "m1_ch263"
    run(store, snap, sw)
    _late_capture(snap, k, "0_tie", 0, 100, snap / ms.cid(k))
    run(store, snap, sw)
    assert json.loads((store / "status" / "late_0_tie.json").read_text())["reason"] == "on_time_but_delivered_after_slot_decided"
    assert not (store / "status" / "dup_0_tie.json").exists()
