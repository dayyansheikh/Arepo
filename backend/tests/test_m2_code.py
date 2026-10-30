# ruff: noqa: E501
"""M2 (CH264) code tests, part 1: the code-freeze list of MEASUREMENT_M2_CH264.md (l.19, section 22), the M1 defect classes (slot decided only once now >= grid + 6 h,
k - 1 from the chain status, late / duplicate / off-grid side files, write-once files, sha256 state chain, pins with refusals, dry-run store separation) and J2.
Synthetic tmp trees only (never the host dumps). Each code-freeze item has a test that fails on the J0-era ``m2_j1.py`` (c0538322...51dc)."""

from __future__ import annotations

import copy
import gzip
import importlib.util
import json
import shutil
import sys
from datetime import timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_m2_j1 as t1  # noqa: E402

from astrolabe.research_lab import m2_j1 as m2  # noqa: E402
from astrolabe.research_lab import m2_j2 as cl  # noqa: E402
from astrolabe.research_lab import m2_spec as sp  # noqa: E402

_R = Path(__file__).resolve().parents[1] / "scripts" / "run_m2.py"
_s = importlib.util.spec_from_file_location("run_m2_under_test", _R)
runner = importlib.util.module_from_spec(_s)
sys.modules["run_m2_under_test"] = runner
_s.loader.exec_module(runner)

tcap, cid, iso = t1.tcap, t1.cid, t1.iso
H6 = timedelta(hours=6)


def tspec(readout_days: float = 3.0) -> dict:
    s = sp.dry_spec(t1.WS, t1.WE)
    s["readout_utc"] = sp.iso(t1.WE + readout_days * 86400.0)
    return s


SPEC = tspec()
KW = {"window_start": t1.WS, "window_end": t1.WE, "spec_sha": "a" * 64, "followup_until": tcap(t1.N - 1).timestamp() + 1.0}  # no slot after the last synthetic capture is ever decided


def after(k: int) -> float:
    """A clock value just after capture ``k``'s slot is decidable (grid + 6 h)."""
    return (tcap(k) + H6 + timedelta(seconds=1)).timestamp()


def end_clock(spec=SPEC) -> float:
    return sp.ts(spec, "readout_utc") + 8 * 3600.0


def run(snap, rr, store, now=None, spec=SPEC, **kw):
    return m2.run_pass(snap, rr, store, spec, now=end_clock(spec) if now is None else now, **kw)


def units_of(store: Path) -> list[dict]:
    return t1.read_units(store)


def listing(root: Path, sub: str) -> dict:
    return t1.files(root, sub)


@pytest.fixture()
def world(tmp_path):
    snap, rr = t1.build(tmp_path)
    st = tmp_path / "research_lab" / "m2_ch264"
    run(snap, rr, st)
    return snap, rr, st, tmp_path


# --- code-freeze item 1: missing slots are judged by the manifest's finished_utc, never by when J1 runs -----------------------------------

def test_cf1_slot_with_late_finished_utc_is_missing_in_catch_up_exactly_as_live(tmp_path):
    snap = tmp_path / "catchup" / "research_lab" / "snapshots"
    for k in range(t1.N):
        t1.write_capture(snap, k, fin_after_s=(10 * 3600.0 if k == 5 else 300.0))
    rr = tmp_path / "research_lab" / "stream_gamma_rules"
    t1.write_rules(rr)
    st_c = tmp_path / "catchup" / "store"
    mp = m2.run_j1(snap, rr, st_c, now=tcap(t1.N + 12).timestamp(), **KW)  # one catch-up run, long after
    assert mp.extra["missing_capture"] == 1 and mp.extra["late_capture_ignored"] == 1
    assert not (st_c / "units" / f"{cid(5)}.jsonl.gz").exists() and not (st_c / "status" / f"{cid(5)}.json").exists()
    late = json.loads((st_c / "status" / f"late_{cid(5)}.json").read_text())
    assert late["kind"] == "late_capture_ignored" and late["reason"] == "finished_after_grid_plus_6h"
    # live: the slot is decided at grid + 6 h without the capture; the late one arrives afterwards. The same bytes.
    snap2 = tmp_path / "live" / "research_lab" / "snapshots"
    for k in range(t1.N):
        if k != 5:
            t1.write_capture(snap2, k)
    st_l = tmp_path / "live" / "store"
    m2.run_j1(snap2, rr, st_l, now=after(5), **KW)
    t1.write_capture(snap2, 5, fin_after_s=10 * 3600.0)
    m2.run_j1(snap2, rr, st_l, now=tcap(t1.N + 12).timestamp(), **KW)
    for sub in ("units", "status", "followup", "nofav"):
        assert listing(st_l, sub) == listing(st_c, sub), sub
    assert (st_l / "state.json").read_bytes() == (st_c / "state.json").read_bytes()


def test_cf1_absent_finished_utc_is_not_on_time(tmp_path):
    snap = tmp_path / "research_lab" / "snapshots"
    for k in range(t1.N):
        t1.write_capture(snap, k, fin_after_s=None if k == 6 else 300.0)
    st = tmp_path / "store"
    mp = m2.run_j1(snap, None, st, now=tcap(t1.N + 12).timestamp(), **KW)
    assert mp.extra["missing_capture"] == 1
    assert json.loads((st / "status" / f"late_{cid(6)}.json").read_text())["reason"] == "finished_utc_absent"


def test_cf1_a_slot_is_not_decided_before_its_grid_plus_six_hours(tmp_path):
    snap, rr = t1.build(tmp_path)
    st = tmp_path / "store"
    mp = m2.run_j1(snap, rr, st, now=after(4), **KW)
    assert m2.slot_of(tcap(4).timestamp())[0] == mp.last_slot  # capture 5 exists and is on time, yet its slot waits for grid + 6 h
    assert not (st / "units" / f"{cid(5)}.jsonl.gz").exists()


# --- code-freeze item 2: the rule-ledger lookup takes the latest record by commit time, not list position --------------------------------------

def test_cf2_lookup_takes_the_latest_record_by_commit_time_not_list_position():
    t_d = tcap(10).timestamp()
    older, newer = t_d - 7200.0, t_d - 600.0
    recs = [[newer, "20261020", "row", "scheduled", "s1"], [older, "20261020", "row", "barrier", "s0"]]  # the newer record sits first in the list
    assert m2.lookup_records(recs, {}, t_d, "2026-10-20") == ("scheduled", newer)
    assert m2.lookup_records(list(reversed(recs)), {}, t_d, "2026-10-20") == ("scheduled", newer)
    recs.append([t_d + 60.0, "20261020", "row", "both", "s2"])  # committed after t_d: never read, whatever its position
    assert m2.lookup_records(recs, {}, t_d, "2026-10-20")[0] == "scheduled"
    assert m2.lookup_records([[newer, "20261020", "hash", None, "s0"]], {"s0": "barrier"}, t_d, "2026-10-20")[0] == "barrier"
    assert m2.lookup_records([[newer, "20261020", "hash", None, "zz"]], {}, t_d, "2026-10-20")[0] == "rules_unresolved"


def test_cf2_receiptless_record_is_ordered_by_the_end_of_its_day_file():
    t_d = tcap(10).timestamp()
    recs = [[None, "20261019", "row", "barrier", "a"], [t_d - 3600.0, "20261020", "row", "scheduled", "b"], [None, "20261019", "row", "both", "c"]]
    assert m2.lookup_records(recs, {}, t_d, "2026-10-20")[0] == "scheduled"  # the receipt-time record of the later day beats day-before records
    assert m2.lookup_records([recs[0], recs[2]], {}, t_d, "2026-10-20")[0] == "both"  # ties on the day end fall back to position


# --- code-freeze item 3: a missing slot writes its own status file, so the sha chain has no gap -----------------------------------------------

def test_cf3_missing_slot_writes_its_own_status_and_the_chain_has_no_gap(tmp_path):
    snap = tmp_path / "research_lab" / "snapshots"
    for k in range(t1.N):
        if k != 7:
            t1.write_capture(snap, k)
    rr = tmp_path / "research_lab" / "stream_gamma_rules"
    t1.write_rules(rr)
    st = tmp_path / "store"
    m2.run_j1(snap, rr, st, now=tcap(t1.N + 12).timestamp(), **KW)
    s7 = m2.slot_of(tcap(7).timestamp())[0]
    g = sp.iso(m2.slot_time(s7))
    d = json.loads((st / "status" / f"missing_{g.replace('-', '').replace(':', '')}.json").read_text())
    assert d["kind"] == "missing_capture" and d["slot"] == s7 and d["state_sha256_before"] != d["state_sha256_after"]
    audit = cl.audit_chain(st)
    assert audit["ok"] and s7 in audit["missing_slots"]
    nxt = st / "status" / f"{cid(8)}.json"  # tampering with the next slot's status breaks the chain
    dd = json.loads(nxt.read_text())
    dd["state_sha256_before"] = "0" * 64
    nxt.write_text(json.dumps(dd))
    assert not cl.audit_chain(st)["ok"] and any(b.startswith("sha_break") for b in cl.audit_chain(st)["breaks"])


# --- code-freeze item 4: seen_without_k_minus_1_row (every category; includes an unparseable k - 1 end_date) ---------------------------------

def test_cf4_seen_without_k_minus_1_row_counts_every_category_and_an_unparseable_k_minus_1_end_date(tmp_path):
    old = iso(tcap(0) - timedelta(hours=10))

    def fields(k):
        out = {40: t1.mk("0.80", "0.82", event="e40", cat="sports", end=old)}  # overdue in the fold (seen); no row at k - 1; overdue again at k; sports
        if k == t1.K - 1:
            out.pop(40)
        out[41] = t1.mk("0.80", "0.82", event="e41", end=("" if k == t1.K - 1 else old))  # seen; k - 1 end_date unparseable
        out[42] = t1.mk("0.80", "0.82", event="e42", end=old)  # stock: overdue at k - 1 and k, no class
        return out

    snap = t1.one_market_store(tmp_path, fields)
    mp = m2.run_j1(snap, None, tmp_path / "s", now=tcap(t1.N + 12).timestamp(), **KW)
    assert mp.extra["seen_without_k_minus_1_row"] == 2
    rep = m2.run_j0(snap, None, tcap(0).timestamp(), tcap(t1.N).timestamp(), lookback_slots=3)
    assert rep["side_classes"]["seen_without_k_minus_1_row"] == 2


# --- code-freeze item 5: the design-text pin (and the module and lexicon pins) refuse -----------------------------------------------------

def test_cf5_design_text_pin_and_refusals(tmp_path):
    rec = sp.pin_record()
    assert rec["ok"] and rec["design"]["actual"] == "bb7c27e05d94e6585af09a8e8d5b2add274b149c89035dfe4fe6c8b783f7cbb0" == sp.SPEC["design_sha256"]
    assert len(rec["modules"]) == 8 and rec["lexicon"]["ok"]
    assert sp.spec_sha(sp.SPEC) == sp.SPEC["design_sha256"]  # section 2: spec_sha is the sha256 of the frozen text
    bad = tmp_path / "MEASUREMENT_M2_CH264.md"
    bad.write_text(sp.DESIGN_PATH.read_text() + "\nedit\n")
    with pytest.raises(sp.PinMismatch) as e:
        sp.check_pins(sp.SPEC, design=bad)
    assert e.value.record["design"]["ok"] is False and e.value.record["design"]["expected"] == sp.SPEC["design_sha256"]
    paths = sp.module_paths()
    fake = tmp_path / "costs.py"
    fake.write_text("x = 1\n")
    paths["costs.py"] = fake
    with pytest.raises(sp.PinMismatch) as e2:
        sp.check_pins(sp.SPEC, paths=paths)
    assert e2.value.record["modules"]["costs.py"]["ok"] is False and e2.value.record["modules"]["costs.py"]["actual"] != e2.value.record["modules"]["costs.py"]["expected"]
    with pytest.raises(sp.PinMismatch):
        sp.check_pins(sp.SPEC, lexicon="0" * 64)
    with pytest.raises(sp.PinMismatch):  # the spec_sha / code_sha pins are checked against the running code at every pass
        sp.check_run_pins({"spec_sha": "x", "code_sha": sp.code_sha()}, sp.SPEC)
    sp.check_run_pins({"spec_sha": sp.spec_sha(sp.SPEC), "code_sha": sp.code_sha()}, sp.SPEC)
    with pytest.raises(sp.PinMismatch):  # a missing code file must not silently shrink code_sha
        sp.code_sha_parts((*sp.CODE_FILES, tmp_path / "nope.py"))


def test_constants_agree_between_spec_and_extractor():
    s = sp.SPEC
    assert sp.ts(s, "registered_utc") == m2.REGISTERED_UTC and sp.ts(s, "end_utc") == m2.END_UTC and sp.ts(s, "readout_utc") == m2.READOUT_UTC
    assert sp.grid0(s) == m2.GRID0 and s["grid_s"] == m2.GRID_S and s["tol_s"] == m2.TOL_S and s["missing_after_grid_s"] == m2.MISSING_AFTER_S
    assert s["lookback_slots"] == m2.LOOKBACK_SLOTS and (s["mid_lo"], s["mid_hi"]) == (m2.MID_LO, m2.MID_HI) and s["overdue_s"] == m2.OVERDUE_S
    assert len(sp.window_slots(s)) == 252 and tuple(sp.PINNED_MODULES) == m2.PIN_MODULES
    assert sum(len(s["cells"][k]) for k in s["cells"]) + 24 == 69
    assert s["bootstrap"]["seed"] == 20261125 and s["bootstrap"]["B"] == 10000


# --- M1 defect classes -----------------------------------------------------------------------------------------------------------------

def test_k_minus_1_is_the_capture_the_chain_folded_not_a_later_on_time_duplicate(tmp_path):
    snap, rr = t1.build(tmp_path)
    st = tmp_path / "store"
    m2.run_j1(snap, rr, st, now=after(t1.K - 1), **KW)  # the slot of capture K - 1 is decided and folded; K is not
    t1.write_capture(snap, t1.K - 1, name="dup_earlier_start", start_shift_s=-600.0)  # an earlier-starting on-time copy of that slot arrives afterwards
    m2.run_j1(snap, rr, st, now=tcap(t1.N + 12).timestamp(), **KW)
    us = {u["market_id"]: u for u in units_of(st)}
    assert us[1]["capture_k_minus_1_id"] == cid(t1.K - 1)  # a fresh listing would pick the copy; the chain must not
    late = json.loads((st / "status" / "late_dup_earlier_start.json").read_text())
    assert late["reason"] == "on_time_but_delivered_after_slot_decided"


def test_duplicate_off_grid_and_late_captures_are_write_once_side_files_counted_once(tmp_path):
    snap, rr = t1.build(tmp_path)
    t1.write_capture(snap, 4, name="dup_later_start", start_shift_s=300.0)  # same slot, later start: a duplicate
    t1.write_capture(snap, 6, name="off_grid_one", start_shift_s=3600.0)  # 1 h off its grid time: off grid
    t1.write_capture(snap, 8, name="late_one", fin_after_s=9 * 3600.0, start_shift_s=120.0)  # finished after grid + 6 h: late
    st = tmp_path / "store"
    a = m2.run_j1(snap, rr, st, now=tcap(t1.N + 12).timestamp(), **KW)
    assert (a.extra["duplicate_slot_capture_ignored"], a.extra["off_grid_capture_ignored"], a.extra["late_capture_ignored"]) == (1, 1, 1)
    for n in ("dup_dup_later_start", "offgrid_off_grid_one", "late_late_one"):
        assert (st / "status" / f"{n}.json").exists(), n
    before = listing(st, "status")
    b = m2.run_j1(snap, rr, st, now=tcap(t1.N + 14).timestamp(), **KW)
    assert (b.extra["duplicate_slot_capture_ignored"], b.extra["off_grid_capture_ignored"], b.extra["late_capture_ignored"]) == (0, 0, 0)  # not re-added by a later run
    assert listing(st, "status") == before
    audit = cl.audit_chain(st)
    assert audit["ok"] and (audit["late_capture_ignored"], audit["duplicate_slot_capture_ignored"], audit["off_grid_capture_ignored"]) == (1, 1, 1)


def test_an_empty_snapshot_root_never_records_every_slot_missing(tmp_path):
    snap = tmp_path / "research_lab" / "snapshots"
    snap.mkdir(parents=True)
    st = tmp_path / "store"
    mp = m2.run_j1(snap, None, st, now=tcap(t1.N + 12).timestamp(), **KW)
    assert mp.last_slot is None and not list((st / "status").glob("*.json"))


def test_files_are_write_once_but_an_identical_rewrite_after_a_crash_is_accepted(world):
    _snap, _rr, st, _ = world
    full_units, full_status, full_state = listing(st, "units"), listing(st, "status"), (st / "state.json").read_bytes()
    mp = m2.M2Pass(window_start=t1.WS, dry_run=False, store=st, spec_sha=sp.spec_sha(SPEC), window_end=t1.WE)
    p = next((st / "units").glob("*.gz"))
    with pytest.raises(FileExistsError):
        mp._write_once(p, b"x")  # different bytes: refused
    mp._write_once(p, p.read_bytes())  # identical bytes: accepted
    assert listing(st, "units") == full_units and listing(st, "status") == full_status and (st / "state.json").read_bytes() == full_state


def test_a_crash_between_status_and_state_reruns_the_slot_with_identical_files(tmp_path):
    snap, rr = t1.build(tmp_path)
    st = tmp_path / "store"
    m2.run_j1(snap, rr, st, now=after(t1.K - 1), **KW)
    state_before = (st / "state.json").read_bytes()
    m2.run_j1(snap, rr, st, now=tcap(t1.N + 12).timestamp(), **KW)
    done = {s: listing(st, s) for s in ("units", "status", "followup", "nofav")}
    final_state = (st / "state.json").read_bytes()
    (st / "state.json").write_bytes(state_before)  # the state file lags the status files by the whole second run
    m2.run_j1(snap, rr, st, now=tcap(t1.N + 12).timestamp(), **KW)
    assert {s: listing(st, s) for s in done} == done and (st / "state.json").read_bytes() == final_state


def test_state_written_by_other_code_or_spec_refuses(world):
    snap, rr, st, _ = world
    d = t1.read_state(st)[0]
    d["code_sha"] = "0" * 64
    t1.write_state_header(st, d)
    with pytest.raises(m2.StateOrderError):
        run(snap, rr, st)


def test_resume_refuses_when_the_chain_status_of_the_last_slot_is_missing(tmp_path):
    snap, rr = t1.build(tmp_path)
    st = tmp_path / "store"
    m2.run_j1(snap, rr, st, now=after(t1.K - 1), **KW)
    (st / "status" / f"{cid(t1.K - 1)}.json").unlink()
    with pytest.raises(m2.StateOrderError):
        m2.run_j1(snap, rr, st, now=tcap(t1.N + 12).timestamp(), **KW)


def test_k_minus_1_gone_on_resume_is_no_previous_capture(tmp_path):
    snap, rr = t1.build(tmp_path)
    st = tmp_path / "store"
    m2.run_j1(snap, rr, st, now=after(t1.K - 1), **KW)
    shutil.rmtree(snap / cid(t1.K - 1))  # retention removed k - 1 before the next pass
    mp = m2.run_j1(snap, rr, st, now=tcap(t1.N + 12).timestamp(), **KW)
    assert mp.notes["resume_prev_capture_gone"] == 1 and mp.funnel["no_previous_capture"] > 0 and mp.funnel.get("unit", 0) == 0


def test_the_ledger_stops_merging_once_the_window_is_folded_and_a_pad_is_inert(tmp_path):
    snap, rr = t1.build(tmp_path)
    st_a, st_b = tmp_path / "a", tmp_path / "b"
    a = m2.run_j1(snap, rr, st_a, now=tcap(t1.N + 12).timestamp(), **KW)
    n_records = a.ledger.n_records()
    day = next(rr.glob("*.jsonl"))  # new rule records appear after the window was folded: not merged
    day.write_text(day.read_text() + json.dumps({"kind": "row", "slot": "s9", "key": "m:777", "sha": "zz", "data": {"question": "fomc", "description": "", "resolutionSource": ""}}) + "\n"
                   + json.dumps({"kind": "poll", "slot": "s9", "ok": True, "finished_utc": iso(tcap(t1.K))}) + "\n")
    a2 = m2.run_j1(snap, rr, st_a, now=tcap(t1.N + 14).timestamp(), **KW)
    assert a2.ledger.n_records() == n_records and 777 not in a2.ledger.by_mid
    b = m2.run_j1(snap, rr, st_b, now=tcap(t1.N + 12).timestamp(), pad_ledger=(500, 40), **KW)  # the host dry run pads the ledger to its end-of-window size
    assert sum(1 for m in b.ledger.by_mid if m < 0) == 40 and sum(len(v) for m, v in b.ledger.by_mid.items() if m < 0) == 500
    assert listing(st_a, "units") == listing(st_b, "units")  # a pad changes no unit


def test_post_window_pass_does_not_hold_the_rule_index(tmp_path):
    """MUST 1: after the window was folded a pass loads no second copy of the rule data (old code: by_mid stayed populated on every post-window pass)."""
    snap, rr = t1.build(tmp_path)
    st = tmp_path / "st"
    a = m2.run_j1(snap, rr, st, now=tcap(t1.N + 12).timestamp(), **KW)
    assert a.ledger_closed()
    a2 = m2.run_j1(snap, rr, st, now=tcap(t1.N + 14).timestamp(), **KW)
    assert a2.ledger_closed() and not a2.rules.by_mid and not a2.rules.sha_class
    assert a2.ledger.n_records() == a.ledger.n_records() and a2.rules.info["files"] == 0  # nothing was read
    # a pass handed an already populated index frees it too
    b = m2.M2Pass(window_start=KW["window_start"], window_end=KW["window_end"], rules=m2.RulesIndex.load(rr), dry_run=False, store=st, spec_sha=KW["spec_sha"])
    assert b.ledger_closed() and b.rules.by_mid
    b.merge_rule_ledger()
    assert not b.rules.by_mid


def test_dry_run_pads_the_rule_ledger_by_default(tmp_path, monkeypatch):
    """Code-freeze item 5: without --no-ledger-pad the runner pads the ledger; ledger_records in j1_runs.jsonl shows it."""
    snap, rr = t1.build(tmp_path)
    monkeypatch.setattr(sp, "DRYRUN_LEDGER_PAD", (500, 40))
    logs = {}
    for name, extra in (("padded", []), ("plain", ["--no-ledger-pad"])):
        store = tmp_path / name / "research_lab" / "m2_ch264_dryrun"
        assert runner.main(["j1", "--store", str(store), "--snapshot-root", str(snap), "--rules-root", str(rr), "--dry-run-last-days", "1", *extra]) == 0
        logs[name] = json.loads((store / "logs" / "j1_runs.jsonl").read_text().splitlines()[-1])
    assert logs["padded"]["ledger_records"] == logs["plain"]["ledger_records"] + 500
    assert logs["padded"]["ledger_markets"] == logs["plain"]["ledger_markets"] + 40


def test_j2_j3_need_pins_on_a_real_store_and_the_dumps_cap_guards(tmp_path):
    real = tmp_path / "research_lab" / "m2_ch264"
    assert runner.main(["j2", "--store", str(real)]) == 2 and runner.main(["j3", "--store", str(real)]) == 2
    (tmp_path / "big.bin").write_bytes(b"x" * 4096)
    snap, _ = t1.build(tmp_path / "w")
    assert runner.main(["j1", "--store", str(real), "--snapshot-root", str(snap), "--pins", str(tmp_path / "no.json"), "--data-dumps", str(tmp_path), "--data-dumps-cap-gb", "0.000001"]) == runner.TEMPFAIL


# --- registered entry point: gates, pins, dry-run separation -----------------------------------------------------------------------------

def test_run_pass_refuses_before_registered_utc_and_on_pin_mismatch(tmp_path):
    snap, rr = t1.build(tmp_path)
    real = copy.deepcopy(sp.SPEC)
    with pytest.raises(sp.M2Refusal, match="before REGISTERED_UTC"):
        m2.run_pass(snap, rr, tmp_path / "research_lab" / "m2_ch264", real, now=sp.ts(real, "registered_utc") - 3600.0)
    with pytest.raises(sp.PinMismatch):
        run(snap, rr, tmp_path / "s2", pins={"spec_sha": "bad", "code_sha": sp.code_sha()})
    with pytest.raises(sp.PinMismatch):
        run(snap, rr, tmp_path / "s3", pins={"spec_sha": sp.spec_sha(SPEC), "code_sha": "bad"})
    with pytest.raises(sp.M2Refusal, match="dry run only"):
        m2.run_pass(snap, rr, tmp_path / "s5", real, now=sp.ts(real, "registered_utc") + 3600.0, pad_ledger=(10, 5))
    run(snap, rr, tmp_path / "s4", pins={"spec_sha": sp.spec_sha(SPEC), "code_sha": sp.code_sha()})
    log = [json.loads(x) for x in (tmp_path / "s4" / "logs" / "j1_runs.jsonl").read_text().splitlines()]
    assert log[0]["spec_sha"] == sp.spec_sha(SPEC) and log[0]["peak_rss_mb"] > 0 and "uma" not in json.dumps(log)


def test_a_closed_followup_makes_j1_refuse(world):
    snap, rr, st, _ = world
    (st / "followup_manifest.json").write_text("{}")
    with pytest.raises(sp.M2Refusal, match="follow-up is closed"):
        run(snap, rr, st)


def test_dry_run_store_and_spec_are_separate_from_the_real_ones(tmp_path):
    assert runner.store_ok(Path("/x/research_lab/m2_ch264"), False) and not runner.store_ok(Path("/x/research_lab/m2_ch264"), True)
    assert runner.store_ok(Path("/x/research_lab/m2_ch264_dryrun"), True) and not runner.store_ok(Path("/x/research_lab/m2_ch264_dryrun"), False)
    assert not runner.store_ok(Path("/x/other/m2_ch264"), False)
    snap, rr = t1.build(tmp_path)
    ds = runner.make_dry_spec(snap, 1)
    assert ds["dry_run"] and sp.spec_sha(ds) != sp.spec_sha(sp.SPEC) and ds["registered_utc"] != sp.SPEC["registered_utc"]
    assert ds["design_sha256"] == sp.SPEC["design_sha256"]  # the real pins are kept: only the window and spec_sha differ
    store = tmp_path / "research_lab" / "m2_ch264_dryrun"
    assert runner.main(["j1", "--store", str(store), "--snapshot-root", str(snap), "--rules-root", str(rr), "--dry-run-last-days", "1", "--no-ledger-pad"]) == 0
    assert (store / "state.json").exists() and not (tmp_path / "research_lab" / "m2_ch264").exists()
    d = t1.read_state(store)[0]
    assert d["spec_sha"] == sp.spec_sha(ds) != sp.spec_sha(sp.SPEC)
    real_store = tmp_path / "research_lab" / "m2_ch264"
    assert runner.main(["j1", "--store", str(real_store), "--snapshot-root", str(snap), "--dry-run-last-days", "1"]) == 2  # the real store with the dry flag
    assert runner.main(["j1", "--store", str(store), "--snapshot-root", str(snap)]) == 2  # the dry store without it
    assert runner.main(["j2", "--store", str(store), "--dry-run-last-days", "1"]) == 2  # a dry run of another job
    assert runner.main(["j1", "--store", str(real_store), "--snapshot-root", str(snap)]) == 2  # a real j1 without pins
    bad = tmp_path / "pins.json"
    bad.write_text(json.dumps({"spec_sha": "x", "code_sha": "y", "registration_commit_utc": "2026-01-01T00:00:00Z"}))
    assert runner.main(["j1", "--store", str(real_store), "--snapshot-root", str(snap), "--pins", str(bad)]) == 3  # a pin mismatch exits 3


# --- J2 ----------------------------------------------------------------------------------------------------------------------------------

def test_j2_units_manifest(world):
    _snap, _rr, st, _ = world
    with pytest.raises(sp.M2Refusal, match="before END_UTC"):
        cl.close_units(st, SPEC, now=sp.ts(SPEC, "end_utc") + 5 * 3600.0)
    now = sp.ts(SPEC, "end_utc") + 7 * 3600.0
    man = cl.close_units(st, SPEC, now=now)
    assert man["window_slots"] == len(sp.window_slots(SPEC)) and man["slot_coverage"] == 1.0 and man["missing_slots"] == [] and man["units"] == 9 and man["no_favourite_lines"] > 0
    assert f"units/{cid(t1.K)}.jsonl.gz" in man["files"] and f"status/{cid(t1.K)}.json" in man["files"] and all(k.split("/")[0] in ("units", "nofav", "status") for k in man["files"])
    assert man["manifest_sha256"] == sp.sha256_file(st / "manifest.json")
    assert cl.close_units(st, SPEC, now=now + 3600.0)["manifest_sha256"] == man["manifest_sha256"]  # an identical re-run is accepted
    (st / "manifest.json").write_text("{}")
    with pytest.raises(sp.M2Refusal, match="overwrite"):
        cl.close_units(st, SPEC, now=now + 3600.0)


def test_j2_refuses_with_an_undecided_window_slot_or_a_broken_chain(tmp_path):
    snap, rr = t1.build(tmp_path)
    st = tmp_path / "store"
    m2.run_j1(snap, rr, st, window_start=t1.WS, window_end=t1.WE, spec_sha=sp.spec_sha(SPEC), now=after(t1.K))
    with pytest.raises(sp.M2Refusal, match="undecided"):
        cl.close_units(st, SPEC, now=sp.ts(SPEC, "end_utc") + 7 * 3600.0)
    run(snap, rr, st)
    p = st / "status" / f"{cid(t1.K)}.json"
    d = json.loads(p.read_text())
    d["state_sha256_after"] = "f" * 64
    p.write_text(json.dumps(d))
    with pytest.raises(sp.M2Refusal, match="chain ok False"):
        cl.close_units(st, SPEC, now=sp.ts(SPEC, "end_utc") + 7 * 3600.0)


def test_j2_followup_manifest(world):
    _snap, _rr, st, _ = world
    ro_t = sp.ts(SPEC, "readout_utc")
    with pytest.raises(sp.M2Refusal, match="before READOUT_UTC"):
        cl.close_followup(st, SPEC, now=ro_t - 60.0)
    with pytest.raises(sp.M2Refusal, match="no unit manifest"):
        cl.close_followup(st, SPEC, now=ro_t + 60.0)
    cl.close_units(st, SPEC, now=sp.ts(SPEC, "end_utc") + 7 * 3600.0)
    fm = cl.close_followup(st, SPEC, now=ro_t + 60.0)
    assert fm["followup_slots"] == len(sp.followup_slots(SPEC)) > 0
    assert fm["files"] and all(k.startswith("followup/") for k in fm["files"]) and 0 < fm["slot_coverage"] < 1  # captures exist only to the end of the synthetic store
    assert (st / "followup_manifest.json").exists()
    (st / "followup_manifest.json").unlink()  # a follow-up file that differs from the sha256 in its status is never blessed
    f = next((st / "followup").glob("*.gz"))
    f.write_bytes(f.read_bytes() + b"x")
    with pytest.raises(sp.M2Refusal, match="differ from the sha256"):
        cl.close_followup(st, SPEC, now=ro_t + 60.0)


def test_j2_followup_refuses_while_a_slot_is_undecided(tmp_path):
    snap, rr = t1.build(tmp_path)
    st = tmp_path / "store"
    run(snap, rr, st, now=sp.ts(SPEC, "end_utc") + 7 * 3600.0)
    cl.close_units(st, SPEC, now=sp.ts(SPEC, "end_utc") + 7 * 3600.0)
    with pytest.raises(sp.M2Refusal, match="undecided"):
        cl.close_followup(st, SPEC, now=sp.ts(SPEC, "readout_utc") + 60.0)


def test_followup_files_are_blind_and_no_favourite_ids_are_k_visible_only(world):
    _, _, st, _ = world
    fu = sorted((st / "followup").glob("*.gz"))[0]
    lines = [json.loads(x) for x in gzip.open(fu, "rt")]
    assert not {k for x in lines for k in x} & {"bid", "ask", "best_bid", "best_ask", "mid", "price", "outcome", "outcome_trap"}
    nf = [json.loads(x) for p in sorted((st / "nofav").glob("*.gz")) for x in gzip.open(p, "rt")]
    assert nf and all(x["mid_k"] == 0.5 and x["market_id"] == 4 for x in nf) and not any("YES_WON_SECRET" in json.dumps(x) for x in nf)
    assert all(x["spec_sha"] == sp.spec_sha(SPEC) and x["code_sha"] == sp.code_sha() for x in nf)
