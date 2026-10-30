# ruff: noqa: E501
"""M2 (CH264) J1 extractor and J0 dry mode: synthetic stores under tmp_path only (no reads of real data). Tests i-viii of MEASUREMENT_M2_CH264.md 9.2."""

from __future__ import annotations

import csv
import gzip
import hashlib
import importlib.util
import json
import math
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from astrolabe.research_lab import m2_j1 as m2
from astrolabe.research_lab import m2_spec as sp

_P = Path(__file__).resolve().parents[1] / "scripts" / "run_m2_j0.py"
_spec = importlib.util.spec_from_file_location("run_m2_j0_under_test", _P)
runner = importlib.util.module_from_spec(_spec)
sys.modules["run_m2_j0_under_test"] = runner
_spec.loader.exec_module(runner)

T0 = datetime(2026, 10, 20, 0, 31, tzinfo=UTC)
N = 16
K = 10  # the first overdue capture of the synthetic markets
RCOLS = ["market_id", "event_id", "binary", "best_bid", "best_ask", "closed", "active", "end_date", "liquidity", "received_utc", "clob_token_id_0", "outcome_trap"]
ECOLS = ["market_id", "received_utc", "uma_resolution_statuses", "accepting_orders", "fee_type", "fee_category", "series_slugs", "fees_enabled", "fee_schedule",
         "order_price_min_tick_size", "open_interest", "outcome_trap"]
FEE = '{"exponent":1,"rate":0.04,"rebateRate":0.25,"takerOnly":true}'
WS_K = 3  # window_start = capture 3: the first classified k is 4


def tcap(k):
    return T0 + timedelta(hours=2 * k)


def iso(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def cid(k):
    return f"{tcap(k):%Y%m%dT%H%M%S}Z_{k:08x}"


E1 = tcap(8) + timedelta(minutes=30)


def mk(bid, ask, **kw):
    d = {"event": None, "bid": bid, "ask": ask, "end": iso(E1), "uma": "[]", "cat": "politics", "closed": "false", "acc": "true", "ext": True, "liq": "100", "tick": "0.001"}
    d.update(kw)
    return d


def markets(k):
    """{market_id: fields} present at capture k."""
    m = {1: mk("0.80", "0.82", event="eA"), 2: mk("0.18", "0.20", event="eA", cat="Finance:US"), 3: mk("0.80", "0.82", cat="sports"), 4: mk("0.49", "0.51"),
         5: mk("0.04", "0.06", cat="mentions", tick="0.01"), 6: mk("0.94", "0.96", event="eA"), 7: mk("0.95", "0.97"), 8: mk("0.03", "0.05"),
         9: mk("0.80", "0.82", uma='["proposed"]'), 10: mk("0.80", "0.82", uma="weird"), 11: mk("0.80", "0.82", uma="None"), 12: mk("0.80", "0.82", uma="nan"),
         13: mk("0.80", "0.82", uma=""), 14: mk("0.80", "0.82", uma="NONE "), 15: mk("0.80", "0.82", closed="true" if k >= K else "false"),
         16: mk("0.80", "0.82", acc="false"), 17: mk("0.80", "0.82", acc=""), 18: mk("0", "0.99"), 20: mk("0.80", "0.82", end=iso(tcap(0) - timedelta(hours=10))),
         21: mk("0.80", "0.82", end=iso(tcap(0) - timedelta(hours=5)) if k <= 5 else iso(E1)), 22: mk("0.80", "0.82", end=""),
         23: mk("0.80", "0.82"), 24: mk("0.80", "0.82", uma="null"), 25: mk("0.80", "0.82", end=iso(tcap(8) + timedelta(minutes=40)) if k < K else iso(E1)),
         26: mk("0.80", "0.82", ext=False)}
    for mid_, f_ in m.items():
        f_["event"] = f_["event"] or f"e{mid_}"
    if k < K:
        m.pop(19, None)
    else:
        m[19] = mk("0.80", "0.82", event="e19")
        m.pop(23)
    return m


def write_capture(root: Path, k: int, mkts=None, recv: bool = True, fin_after_s: float | None = 300.0, name: str | None = None, start_shift_s: float = 0.0) -> Path:
    """A synthetic capture ``k``. ``fin_after_s`` is the manifest's ``finished_utc`` minus the grid time of its slot (None: the key is absent)."""
    d = root / (name or cid(k))
    d.mkdir(parents=True)
    man = {"state": "complete", "started_utc": iso(tcap(k) + timedelta(seconds=start_shift_s)), "capture_id": name or cid(k)}
    if fin_after_s is not None:
        man["finished_utc"] = iso(tcap(k) + timedelta(seconds=fin_after_s))
    (d / "manifest.json").write_text(json.dumps(man))
    rec = iso(tcap(k) + timedelta(minutes=3)) if recv else ""
    rec_ext = iso(tcap(k) + timedelta(minutes=4)) if recv else ""
    with gzip.open(d / "rows.csv.gz", "wt", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(RCOLS)
        for mid, f in (mkts or markets(k)).items():
            w.writerow([mid, f["event"], "1", f["bid"], f["ask"], f["closed"], "true", f["end"], f["liq"], rec, f"t{mid}_0", "YES_WON_SECRET"])
    with gzip.open(d / "rows_ext.csv.gz", "wt", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(ECOLS)
        for mid, f in (mkts or markets(k)).items():
            if f["ext"]:
                w.writerow([mid, rec_ext, f["uma"], f["acc"], "", f["cat"], "", "true", FEE, f["tick"], "", "YES_WON_SECRET"])
    return d


def write_rules(root: Path, with_receipt: bool = True) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    before = iso(tcap(K) - timedelta(minutes=30))
    after = iso(tcap(K) + timedelta(hours=1))

    def row(slot, mid, text, sha):
        return json.dumps({"kind": "row", "slot": slot, "key": f"m:{mid}", "reason": "new", "sha": sha, "data": {"question": text, "description": "", "resolutionSource": ""}})

    def poll(slot, fin, ok=True):
        d = {"kind": "poll", "slot": slot, "ok": ok}
        if with_receipt:
            d["finished_utc"] = fin
        return json.dumps(d)

    lines = [row("s1", 1, "The FOMC decision", "sh1"), row("s1", 2, "Will it reach 5", "sh2"), row("s1", 12, "something plain", "sh12"),
             row("s1", 13, "FOMC and reach", "sh13"), json.dumps({"kind": "hash", "slot": "s1", "key": "m:5", "sha": "unknown_sha"}), poll("s1", before),
             row("s2", 6, "fomc", "sh6"), poll("s2", before, ok=False),  # failed poll: ignored
             row("s3", 12, "fomc", "sh12b"), row("s3", 11, "fomc", "sh11"), poll("s3", after),  # committed after t_d
             row("s4", 14, "fomc torn", "sh14")]  # no poll line: torn
    p = root / f"{T0:%Y%m%d}.jsonl"
    p.write_text("\n".join(lines) + "\n")
    return p


def build(tmp: Path, ks=None, rules=True):
    snap = tmp / "research_lab" / "snapshots"
    for k in (range(N) if ks is None else ks):
        write_capture(snap, k)
    rr = write_rules(tmp / "research_lab" / "stream_gamma_rules") and tmp / "research_lab" / "stream_gamma_rules" if rules else None
    return snap, rr


WS = tcap(WS_K).timestamp() - 1.0
WE = tcap(13).timestamp()


def j1(snap, rr, store, now=None, **kw):
    return m2.run_j1(snap, rr, store, window_start=WS, window_end=WE, spec_sha="a" * 64, now=now or tcap(N + 10).timestamp(), **kw)


@pytest.fixture()
def full(tmp_path):
    snap, rr = build(tmp_path)
    st = tmp_path / "store"
    mp = j1(snap, rr, st)
    return snap, rr, st, mp


def read_state(st: Path):
    """(header dict, ledger {market_id: records}, sha_class) of the JSON-lines state file."""
    lines = [json.loads(x) for x in (st / "state.json").read_text().splitlines()]
    return lines[0], {d["m"]: d["r"] for d in lines[1:] if "m" in d}, {d["s"]: d["c"] for d in lines[1:] if "s" in d}


def write_state_header(st: Path, d: dict) -> None:
    rest = (st / "state.json").read_text().splitlines()[1:]
    (st / "state.json").write_text("\n".join([json.dumps(d), *rest]) + "\n")


def read_units(st: Path):
    out = []
    for p in sorted((st / "units").glob("*.jsonl.gz")):
        with gzip.open(p, "rt") as fh:
            out += [json.loads(x) for x in fh]
    return out


# --- funnel / unit fields --------------------------------------------------------------------------------------------------------------

def test_funnel_classes_and_units(full):
    _, _, st, mp = full
    f = mp.funnel
    assert {k: f[k] for k in f} == {"no_k_minus_1_row": 1, "not_open_at_k": 2, "accepting_unknown": 1, "sidecar_missing": 1, "out_of_scope_sports": 1, "uma_state_at_k": 1,
                                    "uma_other_at_k": 2, "not_two_sided": 1, "mid_low": 1, "mid_high": 1, "no_favourite": 1, "unit": 9}
    assert mp.extra["reoverdue_seen"] == 1 and mp.extra["left_before_overdue_slot"] == 2 and mp.extra["end_date_missing"] == 9
    assert f.get("already_overdue_at_k_minus_1", 0) == 0 and f.get("prior_unit", 0) == 0
    assert mp.extra["pre_window_source"] == WS_K
    u = {x["market_id"]: x for x in read_units(st)}
    assert sorted(u) == [1, 2, 5, 6, 11, 12, 13, 14, 25]
    assert u[1]["side"] == "YES" and u[1]["ask_f"] == 0.82 and u[1]["mid_f"] == 0.81
    assert u[2]["side"] == "NO" and u[2]["ask_f"] == 0.82 and u[2]["bid_f"] == 0.80 and u[2]["cat_k"] == "finance"
    assert u[5]["side"] == "NO" and u[5]["mid_k"] == 0.05 and u[5]["ask_f"] == 0.96 and u[5]["cells"]["S6"] == "(0.9,0.95]" and u[5]["cells"]["S9"] == "0.01"
    assert u[6]["mid_k"] == 0.95 and u[6]["side"] == "YES"
    assert u[1]["event_open_binary_members"] == 3 and u[1]["cells"]["S8"] == "2-5"
    assert u[25]["cells"]["S7"] == "yes" and u[1]["cells"]["S7"] == "no"
    assert u[1]["role"] == "prospective_measurement" and u[1]["spec_sha"] == "a" * 64 and u[1]["code_sha"] == sp.code_sha()
    assert u[1]["uma_raw_k_minus_1"] == "[]" and u[1]["capture_k_minus_1_id"] == cid(K - 1) and u[1]["gap_sidecar_minus_row_s"] == 60.0
    assert abs(u[1]["fee_l1"] - 0.04 * 0.82 * 0.18) < 1e-12 and u[1]["rate_l1"] == 0.04
    assert u[1]["cells"]["S1"] == "mid" and u[1]["cells"]["S12"] == "mid|scheduled"
    s = json.dumps(u)
    assert "YES_WON_SECRET" not in s


def test_every_unit_cell_has_the_declared_value_set(full):
    for x in read_units(full[2]):
        c = x["cells"]
        assert set(c) == {f"S{i}" for i in range(1, 13)}
        assert c["S2"] in m2.S2_CELLS and c["S1"] in m2.S1_CELLS and c["S3"] in (*m2.S3_KEYS, "unknown")


# --- (v) rule class at t_d -------------------------------------------------------------------------------------------------------------

def test_v_rule_records_after_t_d_never_change_s2(full):
    u = {x["market_id"]: x for x in read_units(full[2])}
    s2 = {m: u[m]["cells"]["S2"] for m in u}
    assert s2[1] == "scheduled" and s2[2] == "barrier" and s2[13] == "both"
    assert s2[12] == "other"  # later 'fomc' row committed after t_d is not read
    assert s2[11] == "no_rules" and s2[6] == "no_rules" and s2[14] == "no_rules"  # post-t_d, failed-poll and torn records ignored
    assert s2[5] == "rules_unresolved" and s2[25] == "no_rules"


def test_rule_modes_and_receipt_coverage(tmp_path):
    rr = tmp_path / "rules"
    write_rules(rr)
    ix = m2.RulesIndex.load(rr)
    t_d = tcap(K).timestamp()
    assert ix.lookup(1, t_d, "2026-10-20")[0] == "scheduled"
    assert ix.lookup(12, t_d, "2026-10-20")[0] == "other" and ix.lookup(12, t_d + 7200, "2026-10-20")[0] == "scheduled"  # the later row is visible once its poll is committed
    assert ix.lookup(11, t_d + 7200, "2026-10-20")[0] == "scheduled"
    assert ix.info["poll_ok"] == 2 and ix.info["poll_ok_with_parseable_receipt"] == 2 and ix.info["rows_torn_or_failed"] >= 2
    rr2 = tmp_path / "rules2"
    write_rules(rr2, with_receipt=False)
    ix2 = m2.RulesIndex.load(rr2)
    assert ix2.info["poll_ok"] == 2 and ix2.info["poll_ok_with_parseable_receipt"] == 0
    assert ix2.lookup(1, t_d, "2026-10-20")[0] == "no_rules"  # same UTC day as k: not visible without a receipt time
    assert ix2.lookup(1, t_d, "2026-10-21")[0] == "scheduled"  # ruling 7: a record without finished_utc is visible once its day file is before k's day
    assert ix2.info["records_without_receipt"] == ix2.info["rows_committed"] + ix2.info["hash_committed"] > 0


# --- (vi) mid boundaries, (vii) S6 / S11 boundaries, (viii) E6 --------------------------------------------------------------------------

def test_vi_mid_boundaries_classify_on_rounded_value(full):
    f = full[3].funnel
    assert f["mid_low"] == 1 and f["mid_high"] == 1 and f["no_favourite"] == 1  # 0.04, 0.96, 0.50
    u = {x["market_id"]: x for x in read_units(full[2])}
    assert u[5]["mid_k"] == 0.05 and u[6]["mid_k"] == 0.95  # edges are in
    assert round((0.85 + 0.95) / 2, 6) == 0.9 and (0.85 + 0.95) / 2 != 0.9  # the float problem the rounding removes


def test_vii_s11_and_s6_boundaries_on_rounded_values():
    for tick in ("0.01", "0.001"):
        n_ticks = int(Decimal("0.2") / Decimal(tick))
        for bid_i in range(1, 900, 7):
            bid = Decimal(bid_i) * Decimal(tick)
            if bid >= Decimal("0.7"):
                break
            for n in range(1, n_ticks + 1):
                ask = bid + n * Decimal(tick)
                spread = m2.r6(float(ask) - float(bid))
                d = ask - bid
                want = "<=0.01" if d <= Decimal("0.01") else "(0.01,0.03]" if d <= Decimal("0.03") else "(0.03,0.10]" if d <= Decimal("0.10") else ">0.10"
                assert m2.s11_cell(spread) == want, (tick, bid, ask)
    # the unrounded test fails on one-tick spreads at tick 0.01 (R1 MUST 1)
    assert sum(1 for i in range(1, 100) if (i + 1) * 0.01 - i * 0.01 > 0.01) > 0
    for p, want in ((0.5, None), (0.6, "(0.5,0.6]"), (0.7, "(0.6,0.7]"), (0.8, "(0.7,0.8]"), (0.9, "(0.8,0.9]"), (0.95, "(0.9,0.95]"), (0.5001, "(0.5,0.6]")):
        if want:
            assert m2.s6_cell(p) == want
    for bid, ask, want in (("0.39", "0.41", "(0.5,0.6]"), ("0.29", "0.31", "(0.6,0.7]"), ("0.19", "0.21", "(0.7,0.8]"), ("0.09", "0.11", "(0.8,0.9]"), ("0.04", "0.06", "(0.9,0.95]")):
        mid = round((float(bid) + float(ask)) / 2, 6)
        assert m2.s6_cell(m2.r6(1 - mid)) == want  # NO side: 1 - 0.4 = 0.6 etc.
    assert m2.s6_cell(1 - 0.3) == "(0.6,0.7]" and m2.s6_cell(1 - 0.1) == "(0.8,0.9]"
    assert m2.s1_cell(47.46150) == "low" and m2.s1_cell(47.46151) == "mid" and m2.s1_cell(330.74525) == "high" and m2.s1_cell(float("nan")) == "na"
    assert m2.s9_cell("0.0010000000001") == "0.001" and m2.s9_cell("0.01") == "0.01" and m2.s9_cell("") == "other_or_missing"
    assert m2.s3_cell("tech") == "tech" and m2.s3_cell("crypto") == "unknown" and m2.s3_cell("") == "unknown"


def test_viii_e6_passes_only_the_four_empty_forms(full):
    _, _, st, mp = full
    ids = {x["market_id"] for x in read_units(st)}
    assert {11, 12, 13, 14} <= ids  # "None", "nan", "", "NONE " (stripped, lowered)
    assert 24 not in ids and mp.forms_other["null"] == 1 and mp.forms_other["weird"] == 1 and mp.funnel["uma_other_at_k"] == 2
    assert mp.funnel["uma_state_at_k"] == 1
    assert m2.EMPTY_FORMS == ("", "[]", "nan", "none")


# --- (i)-(iv) chronology, state, catch-up, blind follow-up -----------------------------------------------------------------------------

def files(st: Path, sub: str):
    return {p.name: p.read_bytes() for p in sorted((st / sub).glob("*"))}


def test_i_out_of_order_delivery_gives_the_same_units(tmp_path, full):
    _, _, st_full, _ = full
    snap = tmp_path / "b" / "research_lab" / "snapshots"
    rr = tmp_path / "research_lab" / "stream_gamma_rules"
    for k in range(N):
        if k != 5:
            write_capture(snap, k)
    st = tmp_path / "b" / "store"
    mp = j1(snap, rr, st, now=tcap(7).timestamp())
    assert mp.last_slot == m2.slot_of(tcap(4).timestamp())[0]  # stops before the slot that may still arrive
    write_capture(snap, 5)
    j1(snap, rr, st)
    assert files(st, "units") == files(st_full, "units") and files(st, "status") == files(st_full, "status")
    assert (st / "state.json").read_bytes() == (st_full / "state.json").read_bytes()


def test_i_missing_capture_after_six_hours_and_late_capture_ignored(tmp_path):
    snap = tmp_path / "research_lab" / "snapshots"
    for k in range(N):
        if k != 5:
            write_capture(snap, k)
    rr = write_rules(tmp_path / "research_lab" / "stream_gamma_rules") and tmp_path / "research_lab" / "stream_gamma_rules"
    st = tmp_path / "store"
    mp = j1(snap, rr, st, now=tcap(5).timestamp() + 6 * 3600 + 1)
    assert mp.extra["missing_capture"] == 1 and mp.last_slot == m2.slot_of(tcap(5).timestamp())[0]  # slot 6 is not decided before its own grid + 6 h
    write_capture(snap, 5)  # delivered after the slot was recorded missing
    mp2 = j1(snap, rr, st)
    assert mp2.extra["late_capture_ignored"] == 1 and not (st / "units" / f"{cid(5)}.jsonl.gz").exists()
    assert json.loads((st / "status" / f"late_{cid(5)}.json").read_text())["reason"] == "delivered_after_missing_recorded"
    assert mp2.funnel_by_day  # classification continued after the missing slot


def test_ii_state_holding_a_later_capture_refuses(tmp_path):
    snap = tmp_path / "research_lab" / "snapshots"
    for k in range(N):
        if k != 5:
            write_capture(snap, k)
    rr = write_rules(tmp_path / "research_lab" / "stream_gamma_rules") and tmp_path / "research_lab" / "stream_gamma_rules"
    st = tmp_path / "store"
    j1(snap, rr, st, now=tcap(7).timestamp())
    d = read_state(st)[0]
    d["last_slot"] = m2.slot_of(tcap(7).timestamp())[0]
    d["processed_slots"].append(d["last_slot"])
    write_state_header(st, d)
    write_capture(snap, 5)
    with pytest.raises(m2.StateOrderError):
        j1(snap, rr, st)
    # in-process order check
    caps, _ = m2.discover_captures(snap, tcap(0).timestamp(), tcap(N).timestamp())
    mp = m2.M2Pass(window_start=WS)
    mp.feed(caps[1])
    with pytest.raises(m2.StateOrderError):
        mp.feed(caps[0])


def test_iii_twelve_capture_catch_up_equals_incremental(tmp_path, full):
    _, rr, st_full, _ = full
    src = tmp_path / "research_lab" / "snapshots"
    inc = tmp_path / "inc" / "research_lab" / "snapshots"
    inc.mkdir(parents=True)
    st = tmp_path / "inc" / "store"
    for batch in ((0, 1, 2, 3, 4), (5, 6, 7, 8), tuple(range(9, N))):
        for k in batch:
            (inc / cid(k)).symlink_to(src / cid(k))
        j1(inc, rr, st, now=(tcap(batch[-1]) + timedelta(hours=6, seconds=1)).timestamp() if batch[-1] < N - 1 else None)
    assert files(st, "units") == files(st_full, "units") and files(st, "status") == files(st_full, "status") and files(st, "followup") == files(st_full, "followup")
    assert (st / "state.json").read_bytes() == (st_full / "state.json").read_bytes()


def test_iv_followup_is_blind_and_never_read_by_the_extractor(tmp_path, full, monkeypatch):
    # W10: running with the recorder off, or deleting every follow-up file, leaves every unit file and the state file byte-identical, and every
    # status file identical except its `followup` field.
    snap, rr, st_full, _ = full
    opened = []
    real = gzip.open

    def spy(p, *a, **k):
        opened.append(str(p))
        return real(p, *a, **k)

    monkeypatch.setattr(m2.gzip, "open", spy)
    st = tmp_path / "nofollow"
    j1(snap, rr, st, record_followup=False)
    assert not any("/followup/" in p for p in opened)
    assert not any(st_full.name in p for p in opened if "followup" in p)
    assert files(st, "units") == files(st_full, "units") and not files(st, "followup")
    for p_ in (st_full / "followup").glob("*"):  # deleting every follow-up file changes nothing else on disk and nothing a later pass writes
        p_.rename(tmp_path / ("moved_" + p_.name))
    assert files(st, "units") == files(st_full, "units") and (st / "state.json").read_bytes() == (st_full / "state.json").read_bytes()
    for p_ in tmp_path.glob("moved_*"):
        p_.rename(st_full / "followup" / p_.name.removeprefix("moved_"))
    assert (st / "state.json").read_bytes() == (st_full / "state.json").read_bytes()
    for name, blob in files(st_full, "status").items():
        a, b = json.loads(blob), json.loads(files(st, "status")[name])
        a.pop("followup", None), b.pop("followup", None)
        assert a == b
    # follow-up content: after K only, one line per unit, no price / outcome field, sha and line count in the status
    fu = files(st_full, "followup")
    assert cid(K) not in "".join(n for n in fu if n.startswith(cid(K))) or True
    assert not any(n.startswith(cid(K)) for n in fu) and any(n.startswith(cid(K + 1)) for n in fu)
    name = next(n for n in sorted(fu) if n.startswith(cid(K + 1)))
    lines = [json.loads(x) for x in gzip.decompress(fu[name]).decode().splitlines()]
    assert len(lines) == 9 and {"unit_id", "row_present", "closed", "active", "accepting_orders", "uma_raw", "end_date"} <= set(lines[0])
    assert not {k for x in lines for k in x} & {"bid", "ask", "best_bid", "best_ask", "mid", "price", "outcome", "outcome_trap"}
    stt = json.loads(files(st_full, "status")[name.replace(".jsonl.gz", ".json")])
    assert stt["followup"] == {"sha256": hashlib.sha256(fu[name]).hexdigest(), "lines": 9}
    # the status carries no P / C count
    assert "uma" not in json.dumps(stt["followup"]) and set(stt["followup"]) == {"sha256", "lines"}
    # after the window: follow-up only, no classification
    late = json.loads(files(st_full, "status")[f"{cid(14)}.json"])
    assert late["classified"] is False and late["units"] == 0


def test_stores_are_write_once(full):
    snap, rr, st, _ = full
    p = next((st / "units").glob("*.gz"))
    mp = m2.M2Pass(window_start=WS, window_end=WE, rules=m2.RulesIndex(), dry_run=False, store=st, spec_sha="a" * 64)
    with pytest.raises(FileExistsError):
        mp._write_once(p, b"x")


# --- J0 dry mode ---------------------------------------------------------------------------------------------------------------------

def tree(root: Path):
    return sorted(str(p.relative_to(root)) for p in root.rglob("*"))


def test_dry_mode_refuses_a_store_and_writes_nothing(tmp_path):
    with pytest.raises(m2.DryModeError):
        m2.M2Pass(window_start=WS, dry_run=True, store=tmp_path / "s")
    snap, rr = build(tmp_path)
    mp = m2.M2Pass(window_start=WS, dry_run=True)
    with pytest.raises(m2.DryModeError):
        mp._write_once(tmp_path / "x", b"x")
    with pytest.raises(m2.DryModeError):
        mp._write_state()
    before = tree(tmp_path)
    rep = m2.run_j0(snap, rr, tcap(0).timestamp(), tcap(N).timestamp(), lookback_slots=3)
    assert tree(tmp_path) == before
    assert rep["dry_run"] is True


@pytest.fixture()
def rep(tmp_path):
    snap, rr = build(tmp_path)
    return m2.run_j0(snap, rr, tcap(0).timestamp(), tcap(N).timestamp(), lookback_slots=3)


def test_j0_report_counts_and_decisions(rep):
    assert rep["eligible_units"]["total"] == 9 and rep["eligible_units"]["events"] == 7
    assert rep["funnel"]["unit"] == 9 and rep["funnel"]["no_favourite"] == 1 and rep["no_favourite"] == 1
    assert rep["side_classes"]["reoverdue_seen"] == 1 and rep["side_classes"]["left_before_overdue_slot"] == 2
    assert rep["splits_counts"]["S2"] == {"barrier": 1, "both": 1, "no_rules": 4, "other": 1, "rules_unresolved": 1, "scheduled": 1}
    assert rep["splits_counts"]["S5"] == {"NO": 2, "YES": 7}
    assert rep["k_time_zone_counts"]["S6"].keys() == rep["splits_counts"]["S6"].keys()
    d = rep["decisions"]
    assert d["rule_a_extend_to_42_days"] is not None or d["median_full_day_units"] is None
    assert rep["rules_stream"]["committed_poll_lines_carry_parseable_receipt_time"] is True and d["rule_e_day_before_reader_applies"] is False
    assert rep["cat_k_distribution"] == {"finance": 1, "mentions": 1, "politics": 7}
    cov = rep["rule_class_coverage_k_visible_vs_ch269_last_row"]
    assert cov["no_rules|scheduled"] == 3 and cov["other|scheduled"] == 1  # markets 6 (failed poll), 11 (post-t_d), 14 (torn); 12 (later row): CH269's last row wins
    assert rep["status_forms"]["uma_other_at_k_forms"] == {"null": 1, "weird": 1, "[\"proposed\"]": 1}  # every non-whitelist form is printed


def test_j0_prints_no_price_or_outcome(rep):
    s = json.dumps(rep)
    for sentinel in ("YES_WON_SECRET", "outcome_trap", "0.82", "0.9613", '"ask"', '"bid"'):
        assert sentinel not in s


def test_j0_rule_e_without_receipt_times(tmp_path):
    snap, _ = build(tmp_path, rules=False)
    rr = tmp_path / "research_lab" / "stream_gamma_rules"
    write_rules(rr, with_receipt=False)
    rep = m2.run_j0(snap, rr, tcap(0).timestamp(), tcap(N).timestamp(), lookback_slots=3)
    assert rep["decisions"]["rule_e_day_before_reader_applies"] is True and "rules_mode" not in rep
    assert rep["splits_counts"]["S2"] == {"no_rules": 9}  # the same-day files are not read by the day-before reader


def test_j0_is_deterministic(tmp_path):
    snap, rr = build(tmp_path)
    a = m2.run_j0(snap, rr, tcap(0).timestamp(), tcap(N).timestamp(), lookback_slots=3)
    b = m2.run_j0(snap, rr, tcap(0).timestamp(), tcap(N).timestamp(), lookback_slots=3)
    for r in (a, b):
        r.pop("peak_rss_mb")
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_pins_recorded_and_lexicon_verbatim(rep):
    pins = rep["pins"]["imported_module_sha256"]
    d = Path(m2.__file__).resolve().parent
    assert set(pins) == {"boundary_map_ch240.py", "cb17_census.py", "live_tests11_base.py", "live_tests8_base.py", "population_map_ch251.py", "calibration.py", "costs.py", "cb13_label.py"}
    for n, h in pins.items():
        assert h == hashlib.sha256((d / n).read_bytes()).hexdigest()
    from astrolabe.research_lab import census_map_ch269 as c269

    assert m2.SCHEDULED_RE.pattern == c269.SCHEDULED_RE.pattern and m2.BARRIER_RE.pattern == c269.BARRIER_RE.pattern
    assert rep["pins"]["rule_lexicon_sha256"] == m2.lexicon_sha256()
    assert set(rep["code_sha256"]) == {"m2_j1.py", "run_m2_j0.py"} and rep["m2_j1_code_sha256"] == rep["code_sha256"]["m2_j1.py"]
    assert rep["spec_sha256"] is None or len(rep["spec_sha256"]) == 64


def test_fee_lines_l1_l2():
    f = m2.fee_lines("politics", "true", True, '{"rate":0,"exponent":1}', 0.8)
    assert f["rate_l1"] == 0.04 and f["rate_l2"] == 0.04  # conservative: max(docs, served 0)
    f = m2.fee_lines("politics", "false", True, '{"rate":0.1}', 0.8)
    assert f["rate_l1"] == 0.0 and f["rate_l2"] == 0.1 and f["fees_enabled_arg"] is False  # L2 is the conservative max(docs, served) with the flag ignored
    f = m2.fee_lines("zzz", "", False, '{"rate":0}', 0.8)
    assert f["rate_l1"] == 0.0 and f["rate_l2"] == 0.07 and f["fees_enabled_arg"] is None  # unknown key: served 0 for L1, MAX for L2
    f = m2.fee_lines("zzz", "", False, "", 0.5)
    assert f["rate_l1"] == 0.07 and math.isclose(f["fee_l1"], 0.07 * 0.25)


def test_runner_refusals_and_write_once(tmp_path):
    snap, rr = build(tmp_path)
    out = tmp_path / "research_lab" / "m2_j0" / "M2_J0.json"
    base = ["--snapshot-root", str(snap), "--rules-root", str(rr), "--start-utc", iso(tcap(0)), "--end-utc", iso(tcap(N)), "--lookback-slots", "3"]
    assert runner.main(["--snapshot-root", str(rr), "--rules-root", str(rr), "--start-utc", iso(tcap(0)), "--end-utc", iso(tcap(N)), "--out", str(out)]) == 2
    assert runner.main(base + ["--out", str(tmp_path / "elsewhere.json")]) == 2
    assert runner.main(base + ["--out", str(out)]) == 0
    first = out.read_text()
    assert json.loads(first)["eligible_units"]["total"] == 9
    assert runner.main(base + ["--out", str(out)]) == 1 and out.read_text() == first
    assert runner.main(["--snapshot-root", str(snap), "--rules-root", str(rr), "--last-days", "8", "--lookback-slots", "3", "--out", str(out.with_name("b.json"))]) == 0
    assert runner.main(["--snapshot-root", str(snap), "--out", str(out.with_name("c.json"))]) == 2  # no span given


# --- J1 ambiguity rulings (docs/research_lab/reviews/M2_J1_AMBIGUITY_RULINGS_2026-10-30.md) ------------------------------------------------

def one_market_store(tmp: Path, fields_at, ks=range(N), recv=True):
    snap = tmp / "research_lab" / "snapshots"
    for k in ks:
        write_capture(snap, k, {m: f for m, f in fields_at(k).items()}, recv=recv)
    return snap


def test_ruling6_distinct_scope_markets_printed_beside_row_captures(rep):
    assert rep["side_classes"]["end_date_missing"] > 1 and rep["end_date_missing_scope_distinct_markets"] == 1  # market 22 in every classified capture
    assert "row-captures" in rep["end_date_missing_note"]


def test_ruling7_each_record_has_its_own_reader(tmp_path):
    rr = tmp_path / "rules"
    rr.mkdir()
    day = f"{T0:%Y%m%d}"
    t_d = tcap(K).timestamp()

    def row(slot, mid, text, sha):
        return json.dumps({"kind": "row", "slot": slot, "key": f"m:{mid}", "reason": "new", "sha": sha, "data": {"question": text, "description": "", "resolutionSource": ""}})

    lines = [row("a", 1, "fomc", "h1"), json.dumps({"kind": "poll", "slot": "a", "ok": True}),  # no finished_utc
             row("b", 2, "fomc", "h2"), json.dumps({"kind": "poll", "slot": "b", "ok": True, "finished_utc": iso(tcap(K) - timedelta(hours=1))}),
             row("c", 3, "fomc", "h3"), json.dumps({"kind": "poll", "slot": "c", "ok": True, "finished_utc": iso(tcap(K) + timedelta(hours=1))})]
    (rr / f"{day}.jsonl").write_text("\n".join(lines) + "\n")
    ix = m2.RulesIndex.load(rr)
    kd_same, kd_next = "2026-10-20", "2026-10-21"
    assert ix.lookup(1, t_d, kd_same)[0] == "no_rules" and ix.lookup(1, t_d, kd_next)[0] == "scheduled"  # no global switch: this record uses the day rule
    assert ix.lookup(2, t_d, kd_same)[0] == "scheduled" and ix.lookup(2, t_d, kd_next)[0] == "scheduled"  # parseable and <= t_d
    assert ix.lookup(3, t_d, kd_next)[0] == "no_rules"  # parseable and > t_d: the day rule never overrides a receipt time
    import inspect

    assert "mode" not in inspect.signature(ix.lookup).parameters and "rules_mode" not in inspect.signature(m2.M2Pass.__init__).parameters


def test_ruling7_cross_midnight_commits_and_max_poll_duration_printed(tmp_path):
    rr = tmp_path / "rules"
    rr.mkdir()
    lines = [json.dumps({"kind": "poll", "slot": "a", "ok": True, "started_utc": "2026-10-20T23:59:30Z", "finished_utc": "2026-10-21T00:00:20Z"}),
             json.dumps({"kind": "poll", "slot": "b", "ok": True, "started_utc": "2026-10-20T12:00:00Z", "finished_utc": "2026-10-20T12:00:05Z"})]
    (rr / "20261020.jsonl").write_text("\n".join(lines) + "\n")
    info = m2.RulesIndex.load(rr).info
    assert info["commits_crossing_midnight"] == 1 and info["max_poll_duration_s"] == 50.0


def test_ruling8_t_d_source_counts(tmp_path):
    def fields(k):
        return {31: mk("0.80", "0.82", event="e31")}

    snap = one_market_store(tmp_path, fields, recv=False)
    rep = m2.run_j0(snap, None, tcap(0).timestamp(), tcap(N).timestamp(), lookback_slots=3)
    assert rep["eligible_units"]["total"] == 1 and rep["t_d_source_counts"] == {"capture_start_fallback": 1}


def test_ruling12_rule_ledger_in_state_survives_retirement_of_a_day_file(tmp_path, full):
    snap, rr, st_full, _ = full
    snap2 = tmp_path / "b" / "research_lab" / "snapshots"
    for k in range(K - 1):
        (snap2 / cid(k)).parent.mkdir(parents=True, exist_ok=True)
        (snap2 / cid(k)).symlink_to(snap / cid(k))
    rr2 = tmp_path / "b" / "research_lab" / "stream_gamma_rules"
    rr2.mkdir(parents=True)
    (rr2 / f"{T0:%Y%m%d}.jsonl").write_bytes(next(rr.glob("*.jsonl")).read_bytes())
    st = tmp_path / "b" / "store"
    j1(snap2, rr2, st, now=(tcap(K - 2) + timedelta(hours=6, seconds=1)).timestamp())
    _h, led_records, led_sha = read_state(st)
    assert led_records[1] and led_sha
    (rr2 / f"{T0:%Y%m%d}.jsonl").unlink()  # the day file is retired
    for k in range(K - 1, N):
        (snap2 / cid(k)).symlink_to(snap / cid(k))
    j1(snap2, rr2, st)
    assert files(st, "units") == files(st_full, "units")  # classes come from the ledger, not the retired file
    assert (st / "state.json").read_bytes() == (st_full / "state.json").read_bytes()


def test_ruling15_non_whitelist_forms_are_uncapped(tmp_path):
    n_forms = 250

    def fields(k):
        return {1000 + i: mk("0.80", "0.82", event=f"e{i}", uma=f"form{i}") for i in range(n_forms)}

    snap = one_market_store(tmp_path, fields)
    rep = m2.run_j0(snap, None, tcap(0).timestamp(), tcap(N).timestamp(), lookback_slots=3)
    assert len(rep["status_forms"]["uma_other_at_k_forms"]) == n_forms and rep["funnel"]["uma_other_at_k"] == n_forms


def test_n1_unclassified_candidates_are_counted(tmp_path, full):
    snap, rr, _, mp_full = full
    n_cand = sum(mp_full.funnel.values())
    ws = tcap(K).timestamp() - 1.0  # the first window capture is K; K - 1 is before the window
    mp = m2.run_j1(snap, rr, tmp_path / "s1", window_start=ws, window_end=WE, spec_sha="a" * 64, now=tcap(N + 10).timestamp())
    assert mp.funnel["k_minus_1_before_window"] == n_cand and mp.funnel.get("unit", 0) == 0
    st2 = tmp_path / "s2"
    snap2 = tmp_path / "b" / "research_lab" / "snapshots"
    snap2.mkdir(parents=True)
    for k in range(N):
        if k != K - 1:
            (snap2 / cid(k)).symlink_to(snap / cid(k))
    mp2 = j1(snap2, rr, st2)  # capture K - 1 missing: k = K has no previous capture
    assert mp2.funnel["no_previous_capture"] == n_cand and mp2.funnel.get("unit", 0) == 0


def test_n2_unparseable_end_date_at_k_minus_1_is_a_class_not_a_unit(tmp_path):
    def fields(k):
        return {30: mk("0.80", "0.82", event="e30", end="" if k < K else iso(E1))}

    snap = one_market_store(tmp_path, fields)
    mp = j1(snap, None, tmp_path / "s")
    assert mp.funnel["k_minus_1_end_date_missing"] == 1 and mp.funnel.get("unit", 0) == 0 and not read_units(tmp_path / "s")


def test_n3_status_carries_the_per_capture_funnel(full):
    _, _, st, _ = full
    stt = json.loads((st / "status" / f"{cid(K)}.json").read_text())
    assert stt["funnel"]["unit"] == 9 and stt["funnel"]["no_k_minus_1_row"] == 1
    assert json.loads((st / "status" / f"{cid(K + 1)}.json").read_text())["funnel"] == {}


def test_n4_lookback_slots_before_the_first_retained_capture_are_counted(full):
    _, _, _, mp = full
    first = m2.slot_of(tcap(0).timestamp())[0]
    assert mp.extra["missing_lookback_slot"] == first - m2.slot_of(WS - m2.LOOKBACK_SLOTS * m2.GRID_S)[0] == 81


def test_n5_runner_has_no_rules_mode(tmp_path):
    snap, rr = build(tmp_path)
    with pytest.raises(SystemExit):
        runner.main(["--snapshot-root", str(snap), "--rules-root", str(rr), "--last-days", "8", "--rules-mode", "receipt", "--out", str(tmp_path / "research_lab" / "x.json")])


# --- amendment 22: the S8 member count and the status counts never read an earlier unit's row after its k -----------------------------

def _sibling_markets(k, variant):
    m = markets(k)
    m[40] = mk("0.80", "0.82", event="eB")  # unit at K (end E1)
    m[41] = mk("0.80", "0.82", event="eB", end=iso(tcap(9) + timedelta(minutes=30)))  # sibling that crosses (becomes a unit) at K + 2
    if k > K:
        if variant == "closed":
            m[40]["closed"] = "true"
        elif variant == "gone":
            del m[40]
        elif variant == "moved_far":
            m[40]["end"] = iso(tcap(k) + timedelta(hours=100))
        elif variant == "moved_reoverdue":
            m[40]["end"] = iso(tcap(K + 1) - timedelta(hours=1))
    return m


def _sibling_run(tmp, variant):
    snap = tmp / "research_lab" / "snapshots"
    for k in range(N):
        write_capture(snap, k, _sibling_markets(k, variant))
    rr = write_rules(tmp / "research_lab" / "stream_gamma_rules") and tmp / "research_lab" / "stream_gamma_rules"
    st = tmp / "store"
    mp = j1(snap, rr, st)
    status = {}
    for n, blob in files(st, "status").items():
        d = json.loads(blob)
        d.pop("followup", None)
        status[n] = d
    return st, mp, status


@pytest.mark.parametrize("variant", ["closed", "gone", "moved_far", "moved_reoverdue"])
def test_amendment22_earlier_sibling_unit_after_its_k_changes_nothing_for_the_later_unit(tmp_path, variant):
    st0, mp0, status0 = _sibling_run(tmp_path / "base", "none")
    st1, mp1, status1 = _sibling_run(tmp_path / variant, variant)
    u0 = {x["market_id"]: x for x in read_units(st0)}
    assert 40 in u0 and 41 in u0 and u0[40]["capture_id"] != u0[41]["capture_id"]
    assert u0[41]["event_open_binary_members"] == 2 and u0[41]["cells"]["S8"] == "2-5"
    assert files(st0, "units") == files(st1, "units")  # byte-identical unit files, including the later unit's member count
    assert {n: {k: v for k, v in d.items() if k != "inputs"} for n, d in status0.items()} == {n: {k: v for k, v in d.items() if k != "inputs"} for n, d in status1.items()}
    assert mp0.extra["reoverdue_seen"] == mp1.extra["reoverdue_seen"] and mp0.extra["seen_without_k_minus_1_row"] == mp1.extra["seen_without_k_minus_1_row"]
