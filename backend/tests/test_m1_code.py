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
    r1 = ex.run_pass(store, src, sw, SPEC, now=t8 + 3600)  # within 6 h of slot 8: must wait, not skip ahead
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
    ex.run_pass(store, snap, sw, SPEC, now=ms.tcap(ms.L + 3).timestamp() + 1800)  # k = 6, 7, 8, 9 processed
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
    ms.write_capture(snap, ms.MISSING_K)  # arrives later
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
    return {"spec_sha": sp.spec_sha(SPEC), "code_sha": sp.code_sha(), "manifest_sha256": man["manifest_sha256"]}


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
    assert res["headline_components"]["theta"]["est"] == pytest.approx(res["headline_components"]["theta"]["est"])
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
