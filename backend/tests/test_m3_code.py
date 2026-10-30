# ruff: noqa: E501
"""M3 (CH274, "the wait") J1 / J0 code tests: synthetic tmp trees only (never the host dumps). Tests (i)-(xvi) of MEASUREMENT_M3_CH274.md 10.2, every defect class of section 17 and
every funnel class of 3.3. The synthetic markets are scripted per capture k on the 2 h grid from 2026-10-20T00:31Z; the window is captures 4..13, captures 0..3 are the look-back
fold, captures 14 and 15 are follow-up only."""

from __future__ import annotations

import copy
import csv
import gzip
import importlib.util
import json
import math
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from astrolabe.research_lab import m3_j1 as m3
from astrolabe.research_lab import m3_spec as sp

_R = Path(__file__).resolve().parents[1] / "scripts" / "run_m3.py"
_s = importlib.util.spec_from_file_location("run_m3_under_test", _R)
runner = importlib.util.module_from_spec(_s)
sys.modules["run_m3_under_test"] = runner
_s.loader.exec_module(runner)

T0 = datetime(2026, 10, 20, 0, 31, tzinfo=UTC)
N = 16
WS_K, WE_K = 4, 14
RCOLS = ["market_id", "event_id", "binary", "best_bid", "best_ask", "closed", "active", "end_date", "liquidity", "received_utc", "clob_token_id_0", "outcome_trap"]
ECOLS = ["market_id", "received_utc", "uma_resolution_statuses", "accepting_orders", "created_at", "fee_type", "fee_category", "series_slugs", "fees_enabled", "fee_schedule",
         "order_price_min_tick_size", "neg_risk_market_id", "outcome_trap"]
FEE0 = '{"exponent":1,"rate":0,"rebateRate":0,"takerOnly":true}'
FEE4 = '{"exponent":1,"rate":0.04,"rebateRate":0.25,"takerOnly":true}'
H6 = timedelta(hours=6)


def tcap(k):
    return T0 + timedelta(hours=2 * k)


def iso(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def cid(k):
    return f"{tcap(k):%Y%m%dT%H%M%S}Z_{k:08x}"


WS = tcap(WS_K).timestamp() - 1.0
WE = tcap(WE_K).timestamp()
FAR = "2027-03-01T00:00:00Z"
OLD = "2026-09-01T00:00:00Z"
UP = [(0, ("0.91", "0.93")), (7, ("0.95", "0.96")), (8, ("0.96", "0.97"))]  # the clean crossing at k = 7


def at(lst, k):
    v = None
    for k0, x in lst:
        if k0 <= k:
            v = x
    return v


def mk(px=UP, **kw):
    d = {"event": None, "px": px, "uma": [(0, "[]")], "end": FAR, "created": OLD, "cat": "politics", "closed": [(0, "false")], "acc": "true", "ext": True, "liq": "5000", "tick": "0.001",
         "fe": "false", "fsch": FEE0, "present": (0, 99)}
    d.update(kw)
    return d


def worlds_markets() -> dict:
    t7 = tcap(7) + timedelta(minutes=4)  # t_d of a k = 7 unit
    m = {
        1: mk(event="e1", uma=[(0, "[]"), (10, '["proposed"]')]),
        2: mk(px=[(0, ("0.06", "0.08")), (7, ("0.03", "0.05"))], event="e2", cat="Finance:US", fsch=FEE4, fe="true"),
        3: mk(px=[(0, ("0.96", "0.97"))]),  # near at its first row (look-back): left censored, never a unit
        4: mk(px=[(0, ("0.91", "0.93")), (2, ("0.96", "0.97")), (5, ("0.91", "0.93")), (8, ("0.96", "0.97"))]),  # near in the look-back, back above 0.95 at k = 8: never a unit
        5: mk(px=[(0, ("0.50", "0.52")), (7, ("0.96", "")), (8, ("0.96", "0.97"))]),  # first near state is one-sided
        6: mk(px=[(0, ("0.50", "0.52")), (7, ("0.30", "0.96")), (9, ("0.95", "0.96"))]),  # wide book at 7, ask already 0.96 at k - 1 = 8
        7: mk(px=[(0, ("0.91", "0.93")), (6, ("", "0.93")), (7, ("0.95", "0.96"))]),  # k - 1 one-sided
        8: mk(created="2026-10-20T10:00:00Z"),  # young
        9: mk(end=iso(t7 + timedelta(hours=10))),  # end within 24 h (end = t_d + 10 h)
        10: mk(cat="sports"),
        11: mk(cat="crypto"),
        12: mk(uma=[(0, "[]"), (7, '["proposed"]')]),
        13: mk(uma=[(0, "[]"), (7, "weird")]),
        14: mk(uma=[(0, "[]"), (7, "None ")]),
        15: mk(uma=[(0, "[]"), (7, "nan")]),
        16: mk(uma=[(0, "[]"), (7, "NONE")]),
        17: mk(uma=[(0, "[]"), (7, "null")]),
        18: mk(uma=[(0, "")]),
        19: mk(closed=[(0, "false"), (7, "true")]),
        20: mk(acc=""),
        21: mk(acc="false"),
        22: mk(ext=False),
        23: mk(end=""),
        24: mk(px=[(0, ("0.50", "0.52")), (7, ("0.97", "0.95"))]),  # crossed
        25: mk(px=[(0, ("0.50", "0.52")), (7, ("0.95", "1.0"))]),  # ask exactly 1.0: not a resting order, one-sided bid near
        26: mk(px=[(0, ("0.50", "0.52")), (7, ("0", "0.04"))]),  # bid exactly 0: unusable, ask-only <= 0.05
        27: mk(px=[(0, ("0.85", "0.93")), (7, ("0.85", "0.95"))]),  # mid exactly 0.90 at the line
        28: mk(px=[(0, ("0.91", "0.93")), (7, ("0.94", "0.949999")), (8, ("0.95", "0.96"))]),  # 0.949999 is below the line; the crossing is at k = 8
        29: mk(created=iso(tcap(7) - timedelta(hours=24))),  # age exactly 24 h: passes
        30: mk(created=iso(tcap(7) - timedelta(hours=24) + timedelta(seconds=1))),  # one second young
        31: mk(end=iso(t7 + timedelta(hours=24))),  # H_k exactly 24 h: end_within_24h
        32: mk(end=iso(t7 + timedelta(hours=24, seconds=1))),  # one second more: a unit
        33: mk(event="eL"),
        34: mk(px=[(0, ("0.50", "0.52"))], event="eL"),
        35: mk(px=[(0, ("0.50", "0.52"))], event="eL"),
        36: mk(event=""),  # empty event id: its own cluster
        37: mk(px=[(0, ("0.91", "0.93")), (13, ("0.95", "0.96"))]),  # day 2026-10-21: the day file is absent
        38: mk(px=[(0, ("0.91", "0.93")), (13, ("0.95", "0.96"))]),  # same, with a visible record from the 10-20 file
        39: mk(px=[(0, ("0.91", "0.93")), (7, ("0.95", "0.96"))], event="e39", fe="false"),  # literal served false fee flag (cat politics)
    }
    for mid, f in m.items():
        if f["event"] is None:
            f["event"] = f"e{mid}"
    return m


def is_present(f: dict, k: int) -> bool:
    p = f["present"]
    return any(lo <= k <= hi for lo, hi in ([p] if isinstance(p, tuple) else p))


def eff(f: dict, k: int) -> dict:
    """The market's fields at capture ``k``: ``alt = (k_from, overrides)`` replaces fields from capture ``k_from`` on (used to change a unit's market after its k)."""
    alt = f.get("alt")
    return {**f, **alt[1]} if alt and k >= alt[0] else f


def write_capture(root: Path, k: int, mkts: dict, fin_after_s: float | None = 300.0, name: str | None = None, start_shift_s: float = 0.0, ext_recv: bool = True) -> Path:
    """A synthetic capture ``k``. ``fin_after_s`` is the manifest's ``finished_utc`` minus the grid time of its slot (None: the key is absent)."""
    d = root / (name or cid(k))
    d.mkdir(parents=True)
    man = {"state": "complete", "started_utc": iso(tcap(k) + timedelta(seconds=start_shift_s)), "capture_id": name or cid(k)}
    if fin_after_s is not None:
        man["finished_utc"] = iso(tcap(k) + timedelta(seconds=fin_after_s))
    (d / "manifest.json").write_text(json.dumps(man))
    rec, rec_ext = iso(tcap(k) + timedelta(minutes=3)), iso(tcap(k) + timedelta(minutes=4)) if ext_recv else ""
    with gzip.open(d / "rows.csv.gz", "wt", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(RCOLS)
        for mid, f in mkts.items():
            f = eff(f, k)
            if not is_present(f, k):
                continue
            bid, ask = at(f["px"], k)
            w.writerow([mid, f["event"], "1", bid, ask, at(f["closed"], k), "true", f["end"], f["liq"], rec, f"t{mid}_0", "YES_WON_SECRET"])
    with gzip.open(d / "rows_ext.csv.gz", "wt", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(ECOLS)
        for mid, f in mkts.items():
            f = eff(f, k)
            if f["ext"] and is_present(f, k):
                w.writerow([mid, rec_ext, at(f["uma"], k), f["acc"], f["created"], "", f["cat"], "", f["fe"], f["fsch"], f["tick"], "nr", "YES_WON_SECRET"])
    return d


def write_rules(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    before = iso(tcap(6) - timedelta(minutes=30))
    earlier = iso(tcap(5))
    later = iso(tcap(9))

    def row(slot, mid, text, sha):
        return json.dumps({"kind": "row", "slot": slot, "key": f"m:{mid}", "reason": "new", "sha": sha, "data": {"question": text, "description": "", "resolutionSource": ""}})

    def poll(slot, fin, ok=True):
        return json.dumps({"kind": "poll", "slot": slot, "ok": ok, "started_utc": fin, "finished_utc": fin})

    lines = [row("s1", 1, "The FOMC decision", "sh1"), row("s1", 2, "Will it reach 5 by March 2027", "sh2"), json.dumps({"kind": "hash", "slot": "s1", "key": "m:33", "sha": "unknown_sha"}),
             row("s1", 38, "plain text", "sh38"), row("s1", 8, "fomc", "sh8"), poll("s1", before),
             row("s2", 1, "it will reach 5", "sh1b"), poll("s2", later),  # committed after t_d of a k = 7 unit: market 1 keeps "scheduled"
             row("s3", 18, "fomc", "sh18a"), poll("s3", before),  # latest by commit time
             row("s4", 18, "it will reach 7", "sh18b"), poll("s4", earlier),  # listed LATER in the file but committed EARLIER
             row("s5", 12, "fomc torn", "sh12")]  # no poll line: torn
    p = root / f"{T0:%Y%m%d}.jsonl"
    p.write_text("\n".join(lines) + "\n")
    return p


def build(tmp: Path, mkts: dict | None = None, ks=None, rules: bool = True, **kw):
    snap = tmp / "research_lab" / "snapshots"
    snap.mkdir(parents=True, exist_ok=True)
    mkts = worlds_markets() if mkts is None else mkts
    for k in (range(N) if ks is None else ks):
        write_capture(snap, k, mkts, **kw)
    rr = tmp / "research_lab" / "stream_gamma_rules"
    if rules:
        write_rules(rr)
    return snap, (rr if rules else None)


def tspec(readout_days: float = 3.0) -> dict:
    s = sp.dry_spec(WS, WE)
    s["readout_utc"] = sp.iso(WE + readout_days * 86400.0)
    return s


SPEC = tspec()
SPEC["readout_utc"] = sp.iso(tcap(N - 1).timestamp() + 1.0)  # no slot after the last synthetic capture is ever decided


def after(k: int) -> float:
    """A clock value just after capture ``k``'s slot is decidable (grid + 6 h)."""
    return (tcap(k) + H6 + timedelta(seconds=1)).timestamp()


def run(snap, rr, store, now=None, spec=SPEC, **kw):
    return m3.run_pass(snap, rr, store, spec, now=(after(N - 1) if now is None else now), **kw)


def read_units(store: Path) -> list[dict]:
    out = []
    for p in sorted((store / "units").glob("*.jsonl.gz")):
        with gzip.open(p, "rt") as fh:
            out += [json.loads(x) for x in fh]
    return out


def files(root: Path, sub: str) -> dict:
    return {p.name: p.read_bytes() for p in sorted((root / sub).glob("*")) if p.is_file()}


def statuses(store: Path) -> dict:
    return {p.name: json.loads(p.read_text()) for p in sorted((store / "status").glob("*.json"))}


def strip_blind(d: dict) -> dict:
    return {k: v for k, v in d.items() if k not in ("followup", "proposals")}


@pytest.fixture()
def world(tmp_path):
    snap, rr = build(tmp_path)
    st = tmp_path / "research_lab" / "m3_ch274_dryrun"
    run(snap, rr, st)
    return snap, rr, st, tmp_path


def funnel_totals(store: Path) -> dict:
    tot: dict = {}
    for d in statuses(store).values():
        for k, v in (d.get("funnel") or {}).items():
            tot[k] = tot.get(k, 0) + v
    return tot


def counts_totals(store: Path) -> dict:
    tot: dict = {}
    for d in statuses(store).values():
        for k, v in (d.get("counts") or {}).items():
            if k not in ("near_seen_size", "near_seen_in_scope"):
                tot[k] = tot.get(k, 0) + v
    return tot


# --- 3.2 / 3.3: the near-certain state, the funnel classes and the unit fields -----------------------------------------------------------

def test_every_funnel_class_and_the_unit_set(world):
    _, _, st, _ = world
    f = funnel_totals(st)
    # k = 4 is the first window capture (k - 1 = 3 is before the window): its near candidates are counted k_minus_1_before_window; none are units
    assert f["first_near_one_sided"] == 3  # markets 5 (bid only), 25 (ask 1.0 is no ask), 26 (bid 0 is no bid)
    c = counts_totals(st)
    assert c["first_near_one_sided:bid_only_ge_095"] == 2 and c["first_near_one_sided:ask_only_le_005"] == 1
    assert f["k_minus_1_not_two_sided"] == 1 and c["k_minus_1_not_two_sided:one_sided"] == 1  # market 7
    assert f["ask_not_crossed"] == 1  # market 6 at k = 9: its ask was already 0.96 at k - 1, N failed on the mid clause
    assert f["not_open_at_k"] == 2  # markets 19 (closed) and 21 (accepting false)
    assert f["accepting_unknown"] == 1 and f["sidecar_missing"] == 1
    assert f["out_of_scope_sports"] == 1 and f["out_of_scope_crypto"] == 1
    assert f["uma_state_at_k"] == 1 and f["uma_other_at_k"] == 2  # markets 12; 13 and 17 (null is not an empty form)
    assert f["end_date_missing"] == 1 and f["end_within_24h"] == 2  # markets 23; 9 and 31 (exactly 24 h)
    assert f["young_at_k"] == 2  # markets 8 and 30 (one second short of 24 h)
    assert f.get("created_at_missing", 0) == 0 and f.get("created_at_after_k", 0) == 0
    assert f.get("prior_unit", 0) == 0 and f.get("near_seen_but_candidate", 0) == 0 and f.get("no_previous_capture", 0) == 0
    assert c["crossed_book"] >= 1 and c["wide_book_high_ask"] >= 1
    us = {u["market_id"]: u for u in read_units(st)}
    assert sorted(us) == [1, 2, 14, 15, 16, 18, 27, 28, 29, 32, 33, 36, 37, 38, 39]
    assert f["unit"] == len(us)
    assert us[28]["k_start_utc"] == iso(tcap(8)) and us[1]["k_start_utc"] == iso(tcap(7))  # 0.949999 is not near: market 28's crossing is a capture later
    assert us[37]["k_start_utc"] == iso(tcap(13))


def test_unit_fields_and_k_visible_only(world):
    _, _, st, _ = world
    us = {u["market_id"]: u for u in read_units(st)}
    u1, u2, u27, u33, u36 = us[1], us[2], us[27], us[33], us[36]
    assert u1["side"] == "YES" and u1["ask_f"] == 0.96 and u1["bid_f"] == 0.95 and u1["mid_f"] == 0.955 and u1["ask_f_k_minus_1"] == 0.93
    assert u1["c_discount"] == 0.04 and u1["half_spread"] == 0.005 and u1["role"] == "prospective_measurement"
    assert u1["t_d_source"] == "receipt" and u1["gap_sidecar_minus_row_s"] == 60.0 and u1["capture_k_minus_1_id"] == cid(6) and u1["uma_raw_k_minus_1"] == "[]"
    assert u1["spec_sha"] == sp.spec_sha(SPEC) and u1["code_sha"] == sp.code_sha()
    assert u2["side"] == "NO" and u2["ask_f"] == 0.97 and u2["bid_f"] == 0.95 and u2["mid_f"] == 0.96 and u2["cat_k"] == "finance" and u2["ask_f_k_minus_1"] == 0.94
    assert abs(u2["fee_l1"] - 0.04 * 0.97 * 0.03) < 1e-12
    assert u27["mid_k"] == 0.9 and u27["mid_f"] == 0.9  # the rounded mid sits exactly on the 0.90 line and passes
    assert u33["event_open_binary_members"] == 3 and u33["cells"]["S8"] == "2-5" and u33["cells"]["S6"] == "member_yes"
    assert u36["event_id"] == "market:36" and u36["cells"]["S6"] == "standalone" and u36["cells"]["S8"] == "1"
    assert u1["cells"]["S7"] == "YES" and u2["cells"]["S7"] == "NO" and u2["cells"]["S6"] == "standalone"
    assert u1["cells"]["S1"] == "1k-10k" and u1["cells"]["S11"] == "[0.96,0.97)" and u1["cells"]["S12"] == "0.001" and u1["cells"]["S13"] == "days 1-7"
    assert u1["cells"]["S4"] == ">= 43 d"
    assert u1["cells"]["S5"] == f"{u1['cells']['S2']}|{u1['cells']['S4']}"
    for u in us.values():
        assert set(u["cells"]) == {f"S{i}" for i in range(1, 14)} and u["cells"]["S10"] in ("fee_free", "fee_on", "unknown") and u["cells"]["S9"] in sp.SPEC["cells"]["S9"]
        assert u["hours_to_end_s"] > 86400.0 and u["age_k_s"] >= 86400.0 and u["mid_f"] >= 0.9 and u["ask_f"] >= 0.95 and u["ask_f_k_minus_1"] < 0.95
    assert us[29]["age_k_s"] == 86400.0 and us[32]["hours_to_end_s"] == 86401.0
    assert "YES_WON_SECRET" not in json.dumps(us)


def test_boundary_values_on_rounded_prices():
    rb = m3.read_book
    assert rb("0.95", "1.0")[0] == "bid_only" and rb("0", "0.04")[0] == "ask_only" and rb("0.97", "0.95")[0] == "crossed" and rb("0.95", "0.95")[0] == "crossed"
    assert rb("", "")[0] == "unparseable" and rb("abc", "0.5")[0] == "ask_only" and rb("0.9999996", "0.5")[0] == "ask_only"  # 0.9999996 rounds to 1.0: no resting order
    ns = m3.near_side
    assert ns(*rb("0.94", "0.95")) == ("YES", "two_sided")  # mid 0.945 >= 0.90, ask exactly 0.95
    assert ns(*rb("0.94", "0.949999")) is None
    assert ns(*rb("0.85", "0.95")) == ("YES", "two_sided")  # mid 0.9 after rounding (0.8999999999999999 raw)
    assert ns(*rb("0.84", "0.95")) is None  # mid 0.895
    assert ns(*rb("0.05", "0.06")) == ("NO", "two_sided")  # NO ask 1 - 0.05 = 0.95, NO mid 0.945
    assert ns(*rb("0.05", "0.15")) == ("NO", "two_sided")  # NO ask 0.95, NO mid 1 - 0.10 = 0.90 exactly on the line
    assert ns(*rb("0.05", "0.16")) is None  # NO mid 0.895
    assert m3.wide_book_high_ask(0.30, 0.96) and not m3.wide_book_high_ask(0.95, 0.96)
    assert ns("bid_only", 0.95, None) == ("YES", "bid_only_ge_095") and ns("bid_only", 0.9499, None) is None
    assert ns("ask_only", None, 0.05) == ("NO", "ask_only_le_005") and ns("ask_only", None, 0.0501) is None
    assert ns("bid_only", 0.04, None) is None and ns("ask_only", None, 0.96) is None  # the surviving side alone does not decide it (rule 28)


def test_cell_boundaries():
    assert [m3.s11_cell(x) for x in (0.95, 0.959999, 0.96, 0.97, 0.98, 0.99, 0.999)] == ["[0.95,0.96)", "[0.95,0.96)", "[0.96,0.97)", "[0.97,0.98)", "[0.98,0.99)", "[0.99,1)", "[0.99,1)"]
    assert [m3.s12_cell(x) for x in ("0.001", "0.01", "0.1", "", "x")] == ["0.001", "0.01", "other_or_missing", "other_or_missing", "other_or_missing"]
    d = 86400.0
    assert [m3.s4_cell(x) for x in (d + 1, 3 * d - 1, 3 * d, 14 * d, 43 * d - 1, 43 * d)] == ["[1 d, 3 d)", "[1 d, 3 d)", "[3 d, 14 d)", "[14 d, 43 d)", "[14 d, 43 d)", ">= 43 d"]
    assert [m3.s8_cell(x) for x in (1, 2, 5, 6)] == ["1", "2-5", "2-5", "6+"] and m3.s9_cell("finance") == "finance" and m3.s9_cell("") == "unknown" and m3.s9_cell("sports") == "unknown"
    assert m3.s13_cell(WS + 8 * 86400.0, WS) == "days 8-14" and m3.s13_cell(WS + 22 * 86400.0, WS) == "days 22-28"


def test_e6_passes_only_the_four_empty_forms(world):
    _, _, st, _ = world
    us = {u["market_id"]: u for u in read_units(st)}
    assert {14, 15, 16, 18} <= set(us)  # "None " (trailing space), "nan", "NONE" and "" pass
    assert not ({12, 13, 17} & set(us))  # proposed, "weird" and "null" do not
    assert m3.EMPTY_FORMS == ("", "[]", "nan", "none")


def test_left_censored_and_first_near_one_sided_are_never_later_units(world):
    _, _, st, _ = world
    us = {u["market_id"] for u in read_units(st)}
    assert 3 not in us and 4 not in us and 5 not in us and 6 not in us and 7 not in us  # 5 is one-sided at its first near row though it is two-sided at k = 8
    s = statuses(st)
    lc = sum(d["counts"].get("left_censored_first_row_pre_window", 0) for d in s.values() if d.get("counts"))
    assert lc >= 1  # market 3 (and the look-back stock of near markets)


def test_the_mid_clause_keeps_a_wide_book_out(tmp_path):
    mk_ = {1: mk(px=[(0, ("0.50", "0.52")), (7, ("0.30", "0.96")), (8, ("0.95", "0.96"))])}
    snap, rr = build(tmp_path, mk_, rules=False)
    st = tmp_path / "research_lab" / "m3_ch274_dryrun"
    run(snap, rr, st)
    assert read_units(st) == []
    assert counts_totals(st)["wide_book_high_ask"] >= 1 and funnel_totals(st)["ask_not_crossed"] == 1


# --- 3.5: the rule reader and rules_gap ---------------------------------------------------------------------------------------------------

def test_rule_class_reader_per_record_commit_time_and_gap(world):
    _, _, st, _ = world
    us = {u["market_id"]: u for u in read_units(st)}
    assert us[1]["rule_class"] == "scheduled" and us[1]["occur_by"] == "0"  # the "reach" record committed after t_d changes nothing (test v)
    assert us[2]["rule_class"] == "barrier" and us[2]["occur_by"] == "1"
    assert us[18]["rule_class"] == "scheduled" and us[18]["rule_commit_utc"] is not None  # latest by commit time, not by position in the file (test xv)
    assert us[33]["rule_class"] == "rules_unresolved" and us[33]["occur_by"] == "na"
    assert us[14]["rule_class"] == "no_rules" and us[14]["occur_by"] == "na" and us[14]["cells"]["S3"] == "na"
    # test xvi: day file 20261021 was never merged. A unit with no visible record is rules_gap; one with a visible record keeps its class
    assert us[37]["rule_class"] == "rules_gap" and us[37]["rules_days_unmerged"] == 1
    assert us[38]["rule_class"] == "other" and us[38]["rules_days_unmerged"] == 1
    assert counts_totals(st)["classed_with_gap"] == 1
    assert us[14]["rules_days_unmerged"] == 0


def test_lookup_orders_by_commit_time_then_day_then_position():
    B = datetime(2026, 10, 20, tzinfo=UTC).timestamp()
    recs = [(B + 200.0, "20261020", "row", "barrier/0", "a"), (B + 100.0, "20261020", "row", "scheduled/0", "b"), (None, "20261019", "row", "other/0", "c")]
    assert m3.lookup_records(recs, {}, B + 1000.0, "2026-10-20")[0] == "barrier/0"  # latest commit time wins, whatever the list order
    assert m3.lookup_records(list(reversed(recs)), {}, B + 1000.0, "2026-10-20")[0] == "barrier/0"
    assert m3.lookup_records(recs, {}, B + 150.0, "2026-10-20")[0] == "scheduled/0"  # nothing committed after t_d is visible
    tie = [(B + 100.0, "20261020", "row", "barrier/0", "a"), (B + 100.0, "20261020", "row", "both/0", "b")]
    assert m3.lookup_records(tie, {}, B + 1000.0, "2026-10-20")[0] == "both/0"
    older_day = [(B + 100.0, "20261020", "row", "barrier/0", "a"), (B + 100.0, "20261019", "row", "both/0", "b")]
    assert m3.lookup_records(older_day, {}, B + 1000.0, "2026-10-20")[0] == "barrier/0"  # equal commit time: the later day file wins, never the list position
    nots = [(None, "20261020", "row", "other/0", "c")]
    assert m3.lookup_records(nots, {}, 1e12, "2026-10-20")[0] == "no_rules" and m3.lookup_records(nots, {}, 1e12, "2026-10-21")[0] == "other/0"  # day-before rule
    assert m3.lookup_records([(B + 5.0, "20261020", "hash", None, "zz")], {"zz": "both/1"}, B + 10.0, "2026-10-20")[0] == "both/1"
    assert m3.lookup_records([(B + 5.0, "20261020", "hash", None, "zz")], {}, B + 10.0, "2026-10-20")[0] == "rules_unresolved"


def test_five_patterns_and_deadline_flag():
    cr = m3.classify_rule
    assert cr({"question": "Will X happen by March 2027?", "description": "", "resolutionSource": ""}) == "barrier/1"  # "by <month>" is also a barrier word; the deadline flag is the stricter reading
    assert cr({"question": "q", "description": "between the market creation and the end", "resolutionSource": ""}) == "other/1"
    assert cr({"question": "q", "description": "a consensus of credible reporting", "resolutionSource": ""}) == "consensus/0"
    assert cr({"question": "FOMC at any time", "description": "", "resolutionSource": ""}).startswith("both/")
    assert cr({"question": "the election", "description": "", "resolutionSource": ""}) == "scheduled/0"
    assert cr({"question": "will hit", "description": "", "resolutionSource": ""}) == "barrier/0"


# --- 10.2: strictly chronological, deterministic missing rule, catch-up ------------------------------------------------------------------

def store_files(st: Path) -> dict:
    out = {}
    for sub in ("units", "status", "followup", "proposals"):
        out.update({f"{sub}/{k}": v for k, v in files(st, sub).items()})
    out["state.json"] = (st / "state.json").read_bytes()
    return out


def test_catch_up_in_one_pass_equals_live_pass_by_pass_with_a_late_capture(tmp_path):
    mkts = worlds_markets()
    snap_a = tmp_path / "a" / "research_lab" / "snapshots"
    snap_b = tmp_path / "b" / "research_lab" / "snapshots"
    for snap in (snap_a, snap_b):
        for k in range(N):
            write_capture(snap, k, mkts, fin_after_s=(10 * 3600.0 if k == 9 else 300.0))  # capture 9 finished 10 h after its grid time (an outage)
    rr_a = write_rules(tmp_path / "a" / "research_lab" / "stream_gamma_rules")
    rr_b = write_rules(tmp_path / "b" / "research_lab" / "stream_gamma_rules")
    st_a, st_b = tmp_path / "a" / "research_lab" / "m3_ch274_dryrun", tmp_path / "b" / "research_lab" / "m3_ch274_dryrun"
    run(snap_a, rr_a, st_a)  # catch-up: one pass after everything
    for k in range(WS_K, N):  # live: one pass after each slot is decidable (the first pass is at or after REGISTERED_UTC: the start gate)
        run(snap_b, rr_b, st_b, now=after(k))
    fa, fb = store_files(st_a), store_files(st_b)
    ua = {k: v for k, v in fa.items() if k.startswith("units/")}
    ub = {k: v for k, v in fb.items() if k.startswith("units/")}
    assert ua == ub and len(ua) >= 10  # test (iii): identical unit files, whatever the clock of the run
    assert fa["state.json"] == fb["state.json"]
    assert {k: v for k, v in fa.items() if k.startswith("status/")} == {k: v for k, v in fb.items() if k.startswith("status/")}
    miss = [d for d in statuses(st_a).values() if d["kind"] == "missing_capture" and d["slot"] == m3.slot_of(tcap(9).timestamp())[0]]
    assert len(miss) == 1  # slot 9 is missing because the capture's manifest finished_utc is after grid + 6 h, in both runs
    assert any(p.name.startswith("late_") for p in (st_a / "status").glob("*.json")) and any(p.name.startswith("late_") for p in (st_b / "status").glob("*.json"))


def test_out_of_order_delivery_processes_in_order_and_gives_the_same_units(tmp_path):
    mkts = worlds_markets()
    snap_f = tmp_path / "f" / "research_lab" / "snapshots"
    snap_r = tmp_path / "r" / "research_lab" / "snapshots"
    for k in range(N):
        write_capture(snap_f, k, mkts)
    for k in reversed(range(N)):
        write_capture(snap_r, k, mkts)
    rr_f = write_rules(tmp_path / "f" / "research_lab" / "stream_gamma_rules")
    rr_r = write_rules(tmp_path / "r" / "research_lab" / "stream_gamma_rules")
    a, b = tmp_path / "f" / "research_lab" / "m3_ch274_dryrun", tmp_path / "r" / "research_lab" / "m3_ch274_dryrun"
    run(snap_f, rr_f, a)
    run(snap_r, rr_r, b)
    assert store_files(a) == store_files(b)


def test_missing_capture_is_judged_on_finished_utc_and_recorded_with_its_own_status(tmp_path):
    snap, rr = build(tmp_path, ks=[k for k in range(N) if k != 8])
    st = tmp_path / "research_lab" / "m3_ch274_dryrun"
    run(snap, rr, st)
    s8 = m3.slot_of(tcap(8).timestamp())[0]
    ss = statuses(st)
    miss = [d for d in ss.values() if d["kind"] == "missing_capture"]
    assert s8 in {d["slot"] for d in miss} and sum(1 for d in miss if d["slot"] == s8) == 1
    # the capture after the gap has no previous capture: every candidate there is no_previous_capture, none is a unit
    nxt = ss[f"{cid(9)}.json"]
    assert nxt["classified"] is False and nxt["prev_capture_id"] is None
    assert funnel_totals(st)["no_previous_capture"] == 2  # markets 6 and 28 are newly near at k = 9 with k - 1 missing: counted per candidate, never a unit
    assert all(u["capture_k_id"] != cid(9) for u in read_units(st))


def test_a_slot_is_decided_only_at_grid_plus_6h_and_never_by_the_wall_clock(tmp_path):
    snap, rr = build(tmp_path, ks=[k for k in range(N) if k != 8])
    st = tmp_path / "research_lab" / "m3_ch274_dryrun"
    run(snap, rr, st, now=after(7))
    assert m3.slot_of(tcap(8).timestamp())[0] not in {d["slot"] for d in statuses(st).values() if d["kind"] == "missing_capture"}
    run(snap, rr, st, now=after(8))
    assert m3.slot_of(tcap(8).timestamp())[0] in {d["slot"] for d in statuses(st).values() if d["kind"] == "missing_capture"}


def test_delivered_after_missing_recorded_for_every_on_time_capture(tmp_path):
    mkts = worlds_markets()
    snap, rr = build(tmp_path, mkts, ks=[k for k in range(N) if k != 8])
    st = tmp_path / "research_lab" / "m3_ch274_dryrun"
    run(snap, rr, st)
    write_capture(snap, 8, mkts, name=cid(8))
    write_capture(snap, 8, mkts, name=cid(8) + "b")
    run(snap, rr, st)
    late = {p.name: json.loads(p.read_text()) for p in (st / "status").glob("late_*.json")}
    assert sorted(d["id"] for d in late.values()) == sorted([cid(8), cid(8) + "b"])  # both, not only the first (test xiii)
    assert {d["reason"] for d in late.values()} == {"delivered_after_missing_recorded"}
    assert all(u["capture_k_id"] != cid(8) for u in read_units(st))  # neither is ever processed


def test_on_time_but_delivered_after_slot_decided_and_k_minus_1_stays_the_chain_capture(tmp_path):
    mkts = worlds_markets()
    snap, rr = build(tmp_path, mkts, ks=range(N))
    # a second capture of slot 6 with an EARLIER start (start - 90 s, still on the grid) arrives after the slot was decided with capture 6
    st = tmp_path / "research_lab" / "m3_ch274_dryrun"
    run(snap, rr, st)
    write_capture(snap, 6, mkts, name="0early_" + cid(6), start_shift_s=-90.0)
    run(snap, rr, st)
    p = st / "status" / f"late_0early_{cid(6)}.json"
    assert json.loads(p.read_text())["reason"] == "on_time_but_delivered_after_slot_decided"
    assert [u for u in read_units(st) if u["market_id"] == 1][0]["capture_k_minus_1_id"] == cid(6)  # k - 1 is the chain's capture, not the later pick (test xii)


def test_duplicate_slot_capture_uses_the_start_id_key_and_ties_are_labelled_by_it(tmp_path):
    mkts = worlds_markets()
    snap, rr = build(tmp_path, mkts, ks=[k for k in range(N) if k != 10])
    write_capture(snap, 10, mkts, name="cap_b")
    write_capture(snap, 10, mkts, name="cap_a")  # same start: the (start, id) key picks cap_a
    write_capture(snap, 10, mkts, name="cap_c", start_shift_s=60.0)  # later start
    st = tmp_path / "research_lab" / "m3_ch274_dryrun"
    run(snap, rr, st)
    assert (st / "status" / "cap_a.json").exists() and not (st / "status" / "cap_b.json").exists()
    dups = {p.name for p in (st / "status").glob("dup_*.json")}
    assert dups == {"dup_cap_b.json", "dup_cap_c.json"}  # test xiv: ties by (start, id) are duplicates, not "delivered after slot decided"
    assert not list((st / "status").glob("late_cap_*"))
    # now the early one arrives later still, with an earlier (start, id) key than the kept capture: a different label
    write_capture(snap, 10, mkts, name="cap_0", start_shift_s=0.0)
    run(snap, rr, st)
    assert json.loads((st / "status" / "late_cap_0.json").read_text())["reason"] == "on_time_but_delivered_after_slot_decided"
    assert (st / "status" / "dup_cap_b.json").exists()


def test_off_grid_capture_is_counted_and_never_used(tmp_path):
    mkts = worlds_markets()
    snap, rr = build(tmp_path, mkts)
    write_capture(snap, 9, mkts, name="offgrid", start_shift_s=45 * 60.0)  # 45 min from the grid point: not within the 30 min tolerance
    st = tmp_path / "research_lab" / "m3_ch274_dryrun"
    run(snap, rr, st)
    assert json.loads((st / "status" / "offgrid_offgrid.json").read_text())["kind"] == "off_grid_capture_ignored"
    assert all(d.get("id") != "offgrid" for d in statuses(st).values() if d["kind"] in ("processed", "missing_capture"))
    fu = files(st, "followup")
    assert "offgrid.jsonl.gz" not in fu


def test_state_chain_is_verified_and_a_breach_refuses(tmp_path):
    snap, rr = build(tmp_path)
    st = tmp_path / "research_lab" / "m3_ch274_dryrun"
    run(snap, rr, st, now=after(9))
    run(snap, rr, st, now=after(10))  # a clean resume passes the chain audit
    assert m3.audit_chain(st)["statuses"] > 80
    good_state = (st / "state.json").read_bytes()
    (st / "state.json").write_bytes(good_state.replace(b'"near_seen_in_scope":', b'"near_seen_in_scope":1', 1))
    with pytest.raises(m3.StateOrderError):
        run(snap, rr, st, now=after(11))
    (st / "state.json").write_bytes(good_state)
    p = st / "status" / f"{cid(8)}.json"
    d = json.loads(p.read_text())
    d["state_sha256_before"] = "0" * 64
    p.write_text(json.dumps(d, sort_keys=True, indent=1))
    with pytest.raises(m3.StateOrderError):
        run(snap, rr, st, now=after(11))
    d["state_sha256_before"] = json.loads((st / "status" / f"{cid(7)}.json").read_text())["state_sha256_after"]
    p.write_text(json.dumps(d, sort_keys=True, indent=1))
    p.unlink()  # a deleted chain status
    with pytest.raises(m3.StateOrderError):
        run(snap, rr, st, now=after(11))


def test_deleted_state_with_statuses_refuses(tmp_path):
    snap, rr = build(tmp_path)
    st = tmp_path / "research_lab" / "m3_ch274_dryrun"
    run(snap, rr, st, now=after(8))
    (st / "state.json").unlink()
    with pytest.raises(m3.StateOrderError):
        run(snap, rr, st, now=after(9))


def test_a_state_holding_a_capture_at_or_after_k_refuses(tmp_path):
    snap, rr = build(tmp_path)
    info = m3.discover_all(snap, 0.0, 4.1e9)
    mp = m3.M3Pass(window_start=WS, window_end=WE, dry_run=True)
    mp.last_slot = info["caps"][9]["slot"]  # the state claims it folded slot 9, but captures 0..9 were never processed or recorded missing
    with pytest.raises(m3.StateOrderError):
        mp.run_available(info["caps"], now=after(N), side=info)
    mp2 = m3.M3Pass(window_start=WS, window_end=WE, dry_run=True)
    mp2.feed(info["caps"][5])
    with pytest.raises(m3.StateOrderError):
        mp2.feed(info["caps"][5])  # not strictly after the last folded capture
    with pytest.raises(m3.StateOrderError):
        mp2.feed(info["caps"][7])  # slot 6 is neither processed nor recorded missing


def test_write_once_refuses_to_overwrite(tmp_path):
    snap, rr = build(tmp_path)
    st = tmp_path / "research_lab" / "m3_ch274_dryrun"
    run(snap, rr, st)
    mp = m3.M3Pass(window_start=WS, window_end=WE, dry_run=False, store=tmp_path / "other", spec_sha="a" * 64)
    p = tmp_path / "other" / "units" / "x.jsonl.gz"
    mp._write_once(p, b"abc")
    mp._write_once(p, b"abc")  # identical bytes: an idempotent re-run
    with pytest.raises(FileExistsError):
        mp._write_once(p, b"abd")
    # a re-run over changed data cannot overwrite a unit file that exists
    u = sorted((st / "units").glob("*.jsonl.gz"))[0]
    (st / "state.json").unlink()
    for q in (st / "status").glob("*.json"):
        q.unlink()
    for q in (st / "followup").glob("*"):
        q.unlink()
    for q in (st / "proposals").glob("*"):
        q.unlink()
    u.write_bytes(u.read_bytes() + b"x")
    with pytest.raises(FileExistsError):
        run(snap, rr, st)


def test_the_extractor_refuses_once_the_unit_manifest_exists(tmp_path):
    snap, rr = build(tmp_path)
    st = tmp_path / "research_lab" / "m3_ch274_dryrun"
    run(snap, rr, st, now=after(5))
    (st / "manifest.json").write_text("{}")
    with pytest.raises(sp.M3Refusal):
        run(snap, rr, st, now=after(8))
    (st / "manifest.json").unlink()
    (st / "followup_manifest.json").write_text("{}")
    with pytest.raises(sp.M3Refusal):
        run(snap, rr, st, now=after(8))


# --- the start gate, pins and refusals ---------------------------------------------------------------------------------------------------

def test_start_gate_refuses_before_registered_utc_and_writes_nothing(tmp_path):
    snap, rr = build(tmp_path)
    st = tmp_path / "research_lab" / "m3_ch274_dryrun"
    with pytest.raises(sp.M3Refusal):
        m3.run_pass(snap, rr, st, SPEC, now=sp.ts(SPEC, "registered_utc") - 1.0)
    assert not st.exists() or not any(st.rglob("*.json*"))


def test_a_real_run_needs_a_frozen_design_and_the_registration_lead(tmp_path):
    snap, rr = build(tmp_path)
    st = tmp_path / "research_lab" / "m3_ch274"
    with pytest.raises(sp.M3Refusal, match="not frozen"):
        m3.run_pass(snap, rr, st, sp.SPEC, now=sp.ts(sp.SPEC, "registered_utc") + 3600.0)
    real = copy.deepcopy(sp.SPEC)
    real["design_sha256"] = sp.sha256_file(sp.DESIGN_PATH)
    real["pinned_module_sha256"] = dict(sp.SPEC["pinned_module_sha256"])
    pins = {"spec_sha": sp.spec_sha(real), "code_sha": sp.code_sha()}
    with pytest.raises(sp.M3Refusal, match="registration_commit_utc"):
        m3.run_pass(snap, rr, st, real, now=sp.ts(real, "registered_utc") + 3600.0, pins=pins)
    late = dict(pins, registration_commit_utc=sp.iso(sp.ts(real, "registered_utc") - 23 * 3600.0))
    with pytest.raises(sp.M3Refusal, match="24 h"):
        m3.run_pass(snap, rr, st, real, now=sp.ts(real, "registered_utc") + 3600.0, pins=late)
    # a frozen design whose text differs from the pin is a pin mismatch
    bad = dict(real, design_sha256="0" * 64)
    with pytest.raises(sp.PinMismatch):
        m3.run_pass(snap, rr, st, bad, now=sp.ts(real, "registered_utc") + 3600.0, pins=pins)


def test_pin_mismatch_of_an_imported_module_the_lexicon_and_the_run_pins(tmp_path):
    rec = sp.check_pins(sp.SPEC)
    assert rec["ok"] and all(m["ok"] for m in rec["modules"].values()) and rec["lexicon"]["ok"] and rec["design"]["frozen"] is False
    paths = sp.module_paths()
    fake = tmp_path / "boundary_map_ch240.py"
    fake.write_text("# edited\n")
    paths["boundary_map_ch240.py"] = fake
    with pytest.raises(sp.PinMismatch) as e:
        sp.check_pins(sp.SPEC, paths)
    assert e.value.record["modules"]["boundary_map_ch240.py"]["ok"] is False and e.value.record["modules"]["boundary_map_ch240.py"]["expected"] == sp.SPEC["pinned_module_sha256"]["boundary_map_ch240.py"]
    paths["boundary_map_ch240.py"] = tmp_path / "does_not_exist.py"
    with pytest.raises(sp.PinMismatch):
        sp.check_pins(sp.SPEC, paths)
    with pytest.raises(sp.PinMismatch):
        sp.check_pins(sp.SPEC, lexicon="0" * 64)
    with pytest.raises(sp.PinMismatch):
        sp.check_run_pins({"spec_sha": "x", "code_sha": sp.code_sha()}, SPEC)
    with pytest.raises(sp.PinMismatch):
        sp.check_run_pins({"spec_sha": sp.spec_sha(SPEC), "code_sha": "y"}, SPEC)
    sp.check_run_pins({"spec_sha": sp.spec_sha(SPEC), "code_sha": sp.code_sha()}, SPEC)
    with pytest.raises(sp.PinMismatch, match="missing_code_files"):
        sp.code_sha((*sp.CODE_FILES, tmp_path / "gone.py"))  # a missing code file must not silently shrink code_sha
    # the design text, once frozen, is a pin
    frozen = dict(sp.SPEC, design_sha256="0" * 64)
    with pytest.raises(sp.PinMismatch):
        sp.check_pins(frozen)
    assert sp.spec_sha(frozen) == "0" * 64 and sp.spec_sha(SPEC) != sp.spec_sha(sp.SPEC)


def test_pinned_files_hash_to_the_pins_and_code_files_exist():
    for n, h in sp.SPEC["pinned_module_sha256"].items():
        assert sp.sha256_file(sp.HERE / n) == h, n
    assert set(sp.SPEC["pinned_module_sha256"]) == set(sp.PINNED_MODULES) and len(sp.PINNED_MODULES) == 8
    assert m3.lexicon_sha256() == sp.SPEC["rule_lexicon_sha256"]
    assert all(Path(p).exists() for p in sp.CODE_FILES) and len(sp.code_sha()) == 64


def test_spec_constants_match_the_design_text():
    s = sp.SPEC
    assert (s["registered_utc"], s["end_utc"], s["readout_utc"]) == ("2026-11-24T00:00:00Z", "2026-12-15T00:00:00Z", "2027-01-29T00:00:00Z")
    assert len(sp.window_slots(s)) == 252 and s["lookback_slots"] == 84 and s["bootstrap"]["seed"] == 20261126 and s["bootstrap"]["B"] == 10000
    assert s["j0"]["rule_a_units_below"] == 48 and s["rules_first_day"] == "20261020" and s["coverage_floor"] == 0.95
    assert sum(len(v) for v in s["cells"].values()) + 32 == 84  # S5 = S2 x S4 (32 cells) is not a list
    assert len(s["cells"]["S2"]) == 8 and len(s["cells"]["S9"]) == 10


# --- the blind recorders and no post-k reads ---------------------------------------------------------------------------------------------

def test_followup_file_fields_header_and_no_outcome(world):
    _, _, st, _ = world
    assert not (st / "followup" / f"{cid(7)}.jsonl.gz").exists()  # no unit exists before capture 7's own pass
    with gzip.open(st / "followup" / f"{cid(10)}.jsonl.gz", "rt") as fh:
        lines = [json.loads(x) for x in fh]
    assert lines[0]["kind"] == "header" and lines[0]["start_utc"] == iso(tcap(10)) and lines[0]["finished_utc"] == iso(tcap(10) + timedelta(seconds=300))
    one = [x for x in lines[1:] if x["unit_id"] == "m3:1"][0]
    assert one["uma_raw"] == '["proposed"]' and one["best_bid"] == "0.96" and one["best_ask"] == "0.97" and one["row_present"] is True
    assert set(one) >= {"closed", "active", "accepting_orders", "end_date", "row_received_utc", "sidecar_received_utc"}
    assert "YES_WON_SECRET" not in json.dumps(lines)
    # every unit is recorded at every later capture (also after the window); the units of capture 7 are first recorded at capture 8
    with gzip.open(st / "followup" / f"{cid(15)}.jsonl.gz", "rt") as fh:
        last = [json.loads(x) for x in fh]
    assert len(last) - 1 == len(read_units(st))
    with gzip.open(st / "followup" / f"{cid(8)}.jsonl.gz", "rt") as fh:
        eight = [json.loads(x) for x in fh]
    assert {"m3:1", "m3:2"} <= {x["unit_id"] for x in eight[1:]} and "m3:28" not in {x["unit_id"] for x in eight[1:]}  # k < j: a unit is not in its own k's follow-up
    stt = statuses(st)[f"{cid(10)}.json"]
    assert set(stt["followup"]) == {"sha256", "lines"} and "uma" not in json.dumps(stt["followup"])


def test_status_files_carry_no_follow_up_content(world):
    _, _, st, _ = world
    for d in statuses(st).values():
        s = json.dumps(d)
        assert "proposed" not in s and "YES_WON" not in s
        if d["kind"] == "processed":
            assert not ({"p_count", "c_count", "a99"} & set(d.get("counts", {})))


def test_proposal_set_recorder_lists_in_scope_first_proposals(world):
    _, _, st, _ = world
    with gzip.open(st / "proposals" / f"{cid(10)}.json.gz", "rt") as fh:
        doc = json.loads(fh.readline())
    import base64

    ids = json.loads(gzip.decompress(base64.b64decode(doc["ids_delta_gzip_b64"])))
    full = [sum(ids[: i + 1]) for i in range(len(ids))]
    assert 1 in full and doc["count"] == len(full) and doc["prev_capture_id"] == cid(9)
    # market 12 turned proposed at k = 7 (from empty): it is in capture 7's set
    with gzip.open(st / "proposals" / f"{cid(7)}.json.gz", "rt") as fh:
        d7 = json.loads(fh.readline())
    ids7 = json.loads(gzip.decompress(base64.b64decode(d7["ids_delta_gzip_b64"])))
    assert 12 in [sum(ids7[: i + 1]) for i in range(len(ids7))]
    assert not (st / "proposals" / f"{cid(15)}.json.gz").exists()  # window captures only


def test_removing_both_blind_recorders_leaves_units_and_state_byte_identical(tmp_path):
    mkts = worlds_markets()
    a = tmp_path / "a" / "research_lab"
    b = tmp_path / "b" / "research_lab"
    snap_a, rr_a = build(tmp_path / "a", mkts)
    snap_b, rr_b = build(tmp_path / "b", mkts)
    sa, sb = a / "m3_ch274_dryrun", b / "m3_ch274_dryrun"
    run(snap_a, rr_a, sa)
    run(snap_b, rr_b, sb, record_followup=False, record_proposals=False)
    fa, fb = store_files(sa), store_files(sb)
    assert {k: v for k, v in fa.items() if k.startswith("units/")} == {k: v for k, v in fb.items() if k.startswith("units/")}  # test (iv)
    assert fa["state.json"] == fb["state.json"]  # the recorders feed nothing back
    assert not [k for k in fb if k.startswith(("followup/", "proposals/"))]
    sta, stb = statuses(sa), statuses(sb)
    assert set(sta) == set(stb)
    for k in sta:
        assert strip_blind(sta[k]) == strip_blind(stb[k]), k


def alter_after_k(mkts: dict, mid: int, k_from: int, absent: bool = False) -> dict:
    """Every field of market ``mid`` changed from capture ``k_from`` on (prices, flags, end date, category, tick, event, liquidity, fee fields, sidecar status), or the row removed."""
    m = copy.deepcopy(mkts)
    f = m[mid]
    f["px"] = [*[x for x in f["px"] if x[0] < k_from], (k_from, ("0.10", "0.12"))]
    f["uma"] = [*[x for x in f["uma"] if x[0] < k_from], (k_from, "garbage")]
    over = {"end": "2026-10-21T00:00:00Z", "created": "2026-10-20T20:00:00Z", "cat": "sports", "acc": "false", "tick": "0.5", "liq": "1", "fe": "true", "fsch": FEE4, "event": "eZ",
            "closed": [(0, "true")]}
    if absent:
        over = {"present": (0, k_from - 1)}
    f["alt"] = (k_from, over)
    return m


def test_no_post_k_content_reaches_units_state_or_status(tmp_path):
    """Every field of a unit's market is changed from capture k on. Units, state and statuses (apart from the blind follow-up / proposal fields) are byte-identical; the positive
    control changes the market AT k and then the unit is gone."""
    mkts = worlds_markets()
    base = tmp_path / "base"
    alt = tmp_path / "alt"
    ctl = tmp_path / "ctl"
    # post-k alteration of the clean unit market 1 (k = 7): from capture 8 on, and of the late unit 38 from capture 13 + 1 (the follow-up captures)
    m_alt = alter_after_k(alter_after_k(mkts, 1, 8), 2, 8)
    m_gone = alter_after_k(alter_after_k(mkts, 1, 8, absent=True), 2, 8, absent=True)  # the unit markets' rows vanish after k
    m_ctl = alter_after_k(mkts, 1, 7)  # at k itself: the unit must change
    gone = tmp_path / "gone"
    out = {}
    for name, root, mk_ in (("base", base, mkts), ("alt", alt, m_alt), ("gone", gone, m_gone), ("ctl", ctl, m_ctl)):
        snap, rr = build(root, mk_)
        st = root / "research_lab" / "m3_ch274_dryrun"
        run(snap, rr, st)
        out[name] = st
    fb, fa = store_files(out["base"]), store_files(out["alt"])
    assert {k: v for k, v in fb.items() if k.startswith("units/")} == {k: v for k, v in fa.items() if k.startswith("units/")}
    assert fb["state.json"] == fa["state.json"]
    sb, sa = statuses(out["base"]), statuses(out["alt"])
    assert set(sb) == set(sa)
    for k in sb:
        assert strip_blind(sb[k]) == strip_blind(sa[k]), k
    assert fb != fa  # the blind follow-up files DID change: that is the recorder, the one allowed reader
    fg = store_files(out["gone"])
    assert {k: v for k, v in fb.items() if k.startswith("units/")} == {k: v for k, v in fg.items() if k.startswith("units/")} and fb["state.json"] == fg["state.json"]
    for k, v in statuses(out["gone"]).items():
        assert strip_blind(sb[k]) == strip_blind(v), k
    # positive control: a change at k changes the units
    uc = {u["market_id"] for u in read_units(out["ctl"])}
    assert 1 not in uc and 1 in {u["market_id"] for u in read_units(out["base"])}
    assert store_files(out["ctl"])["state.json"] != fb["state.json"]


def test_the_scan_never_parses_a_near_seen_market_after_its_entry(tmp_path, monkeypatch):
    mkts = worlds_markets()
    snap, rr = build(tmp_path, mkts)
    seen_calls = []
    real = m3.read_book

    def spy(b, a):
        seen_calls.append((b, a))
        return real(b, a)

    monkeypatch.setattr(m3, "read_book", spy)
    info = m3.discover_all(snap, 0.0, 4.1e9)
    mp = m3.M3Pass(window_start=WS, window_end=None, rules=m3.RulesIndex.load(rr), dry_run=True)
    mp.run_available(info["caps"], now=math.inf, side=info)
    # market 1's unit prices (0.96, 0.97) appear at k = 8..15 but are read_book'd only while the market is not in the near-seen set (never at k >= 8 for the touch 0.96/0.97)
    assert 1 in mp.near_seen and 3 in mp.near_seen
    assert seen_calls.count(("0.96", "0.97")) <= 2  # market 3 at its first row (k = 0) and market 4 at k = 2; the post-entry rows of markets 1, 3, 4 are skipped


# --- J0 ------------------------------------------------------------------------------------------------------------------------------------

def tree(root: Path) -> dict:
    return {str(p.relative_to(root)): p.stat().st_size for p in sorted(root.rglob("*")) if p.is_file()}


def test_j0_writes_no_unit_follow_up_or_state_file_and_prints_rule_a(tmp_path):
    snap, rr = build(tmp_path)
    before = tree(tmp_path)
    rep = m3.run_j0(snap, rr, WS - 5 * 7200.0, tcap(N).timestamp(), lookback_slots=4)
    assert tree(tmp_path) == before  # nothing written anywhere (no unit, status, follow-up, proposal or state file)
    assert rep["dry_run"] is True and rep["code_sha"] == sp.code_sha() and rep["code_sha_parts"] == sp.code_sha_parts() and len(rep["seal_sha256"]) == 64
    assert rep["decision_rule"]["rule_a_extend_to_42_days_if_median_full_day_units_below"] == 48
    assert "rule_a_extend_to_42_days" in rep["decisions"] and rep["decisions"]["median_full_day_units"] is None  # no day has 12 classified captures in the synthetic span
    assert rep["eligible_units"]["total"] >= 10 and rep["pins"]["rule_lexicon_sha256"] == sp.SPEC["rule_lexicon_sha256"]
    assert rep["rules_stream"]["days_missing_from_first_day"] == [] and rep["rules_stream"]["contiguous_from_first_day"] is True
    assert "YES_WON_SECRET" not in json.dumps(rep)
    assert set(rep["splits_counts"]) == {f"S{i}" for i in range(1, 14)}
    assert rep["status_forms_at_e6"]["non_whitelist_forms_uncapped"]
    with pytest.raises(m3.DryModeError):
        m3.M3Pass(window_start=WS, dry_run=True, store=tmp_path / "x")


def test_j0_rule_a_fires_below_48_units_a_day_on_full_days(tmp_path):
    mp = m3.M3Pass(window_start=WS, dry_run=True)
    day = "2026-10-20"
    t0 = datetime(2026, 10, 20, 0, 31, tzinfo=UTC).timestamp()
    mp.classified = [{"id": str(i), "start": t0 + i * 7200.0, "slot": i} for i in range(12)]
    mp.units = [{"day": day, "event_id": f"e{i}", "cells": {f"S{j}": "x" for j in range(1, 14)}, "rule_class": "other", "cat_k": "politics", "tier": "lt1k", "gap_sidecar_minus_row_s": 60.0}
                for i in range(47)]
    rep = mp.report_j0(t0, t0 + 86400.0, None, 12)
    assert rep["decisions"]["median_full_day_units"] == 47.0 and rep["decisions"]["rule_a_extend_to_42_days"] is True and rep["decisions"]["rule_b_record_only"] is True
    mp.units.append(dict(mp.units[0], event_id="e47"))
    rep = mp.report_j0(t0, t0 + 86400.0, None, 12)
    assert rep["decisions"]["rule_a_extend_to_42_days"] is False and rep["decisions"]["projected_21_day_units"] == 48 * 21


def test_j0_reads_no_post_k_content_for_a_hypothetical_unit(tmp_path):
    mkts = worlds_markets()
    reps = []
    for name, mm in (("base", mkts), ("alt", alter_after_k(alter_after_k(mkts, 1, 8), 2, 8))):
        snap, rr = build(tmp_path / name, mm)
        r = m3.run_j0(snap, rr, WS - 5 * 7200.0, tcap(N).timestamp(), lookback_slots=4)
        for k in ("peak_rss_mb", "seal_sha256", "inputs"):
            r.pop(k, None)
        reps.append(r)
    assert reps[0] == reps[1]


# --- the runner ----------------------------------------------------------------------------------------------------------------------------

def test_runner_j0_writes_only_out_refuses_overwrite_and_a_bad_root(tmp_path):
    snap, rr = build(tmp_path)
    out = tmp_path / "research_lab" / "m3_ch274_j0" / "M3_J0.json"
    args = ["j0", "--snapshot-root", str(snap), "--rules-root", str(rr), "--last-days", "1", "--lookback-slots", "4", "--out", str(out), "--data-dumps-cap-gb", "500"]
    assert runner.main(args) == 0 and out.exists()
    d = json.loads(out.read_text())
    assert d["code_sha"] == sp.code_sha() and d["dry_run"] is True
    assert runner.main(args) == 1  # write-once
    assert runner.main(["j0", "--snapshot-root", str(tmp_path), "--last-days", "1", "--out", str(out)]) == 2
    assert runner.main(["j0", "--snapshot-root", str(snap), "--last-days", "1", "--out", str(tmp_path / "elsewhere" / "x.json")]) == 2


def test_runner_guards_exit_75_and_j1_refusals(tmp_path, monkeypatch, capsys):
    snap, rr = build(tmp_path)
    out = tmp_path / "research_lab" / "m3_ch274_j0" / "M3_J0b.json"
    monkeypatch.setattr(runner, "DUMPS", tmp_path)
    assert runner.main(["j0", "--snapshot-root", str(snap), "--last-days", "1", "--out", str(out), "--data-dumps-cap-gb", "0"]) == 75
    assert runner.main(["j0", "--snapshot-root", str(snap), "--last-days", "1", "--out", str(out), "--min-free-gb", "1e9"]) == 75
    real_store = tmp_path / "research_lab" / "m3_ch274"
    assert runner.main(["j1", "--store", str(real_store), "--snapshot-root", str(snap)]) == 2  # --pins required for j1
    assert runner.main(["j1", "--store", str(tmp_path / "wrongname"), "--snapshot-root", str(snap), "--pins", "p.json"]) == 2
    pins = tmp_path / "pins.json"
    pins.write_text(json.dumps({"spec_sha": "x", "code_sha": "y"}))
    assert runner.main(["j1", "--store", str(real_store), "--snapshot-root", str(snap), "--pins", str(pins)]) == 2  # the design text is not frozen
    err = capsys.readouterr().err
    assert "not frozen" in err


def test_runner_dry_run_j1_uses_its_own_store_and_exits_3_on_a_pin_mismatch(tmp_path, monkeypatch):
    snap, rr = build(tmp_path)
    st = tmp_path / "research_lab" / "m3_ch274_dryrun"
    assert runner.main(["j1", "--store", str(st), "--snapshot-root", str(snap), "--rules-root", str(rr), "--dry-run-last-days", "3", "--no-pad"]) == 0
    assert (st / "state.json").exists() and list((st / "units").glob("*.jsonl.gz"))
    assert runner.main(["j1", "--store", str(tmp_path / "research_lab" / "m3_ch274"), "--snapshot-root", str(snap), "--dry-run-last-days", "3"]) == 2  # the real store is refused in a dry run
    monkeypatch.setitem(sp.SPEC["pinned_module_sha256"], "costs.py", "0" * 64)
    st2 = tmp_path / "other" / "research_lab" / "m3_ch274_dryrun"
    assert runner.main(["j1", "--store", str(st2), "--snapshot-root", str(snap), "--rules-root", str(rr), "--dry-run-last-days", "3", "--no-pad"]) == 3


def test_state_pad_is_refused_outside_a_dry_run_and_is_inert(tmp_path):
    snap, rr = build(tmp_path)
    real = copy.deepcopy(sp.SPEC)
    real["design_sha256"] = sp.sha256_file(sp.DESIGN_PATH)
    reg = sp.ts(real, "registered_utc")
    pins = {"spec_sha": sp.spec_sha(real), "code_sha": sp.code_sha(), "registration_commit_utc": sp.iso(reg - 48 * 3600.0)}
    with pytest.raises(sp.M3Refusal, match="pad"):
        m3.run_pass(snap, rr, tmp_path / "s", real, now=reg + 3600.0, pins=pins, pad=((10, 5), (10, 5)))
    st = tmp_path / "research_lab" / "m3_ch274_dryrun"
    a = m3.run_pass(snap, rr, st, SPEC, now=after(N - 1), pad=((300, 50), (200, 40)))
    st2 = tmp_path / "other" / "research_lab" / "m3_ch274_dryrun"
    b = m3.run_pass(snap, rr, st2, SPEC, now=after(N - 1))
    assert a["ledger_records"] > b["ledger_records"] and a["ever_seen"] == b["ever_seen"] + 200 and a["near_seen"] == b["near_seen"] + 40
    assert [u["market_id"] for u in read_units(st)] == [u["market_id"] for u in read_units(st2)]  # synthetic negative ids never touch a real market


def test_fee_lines_l1_literal_false_and_l2_unknown_key():
    f = m3.fee_lines("politics", "false", True, FEE4, 0.96)
    assert f["rate_l1"] == 0.0 and f["fee_l1"] == 0.0 and f["rate_l2"] == 0.04 and f["fees_enabled_arg"] is False
    g = m3.fee_lines("politics", "true", True, FEE4, 0.96)
    assert g["rate_l1"] == 0.04 and g["fees_enabled_arg"] is None  # only a literal served false is passed as False
    h = m3.fee_lines("zzz", "", False, FEE0, 0.96)
    assert h["rate_l2"] == 0.07 and h["rate_l1"] == 0.0 and abs(h["fee_l2"] - 0.07 * 0.96 * 0.04) < 1e-12  # unknown key: L2 is MAX_TAKER_RATE, L1 the served 0
    k = m3.fee_lines("geopolitics", "", False, "", 0.96)
    assert k["rate_l1"] == 0.0 and k["rate_l2"] == 0.0


def test_the_lookback_span_is_fixed_and_missing_lookback_slots_are_counted_never_filled(world):
    _, _, st, _ = world
    ss = statuses(st)
    miss = [d for d in ss.values() if d["kind"] == "missing_capture"]
    first_real = m3.slot_of(tcap(0).timestamp())[0]
    lb_start = m3.slot_of(WS - 84 * 7200.0)[0]
    assert min(d["slot"] for d in miss) == lb_start and len([d for d in miss if d["slot"] < first_real]) == first_real - lb_start
    assert funnel_totals(st).get("unit", 0) == len(read_units(st))
    log = [json.loads(x) for x in (st / "logs" / "j1_runs.jsonl").read_text().splitlines()]
    assert log[-1]["counts"]["missing_lookback_slot"] == first_real - lb_start


def test_pre_window_manifests_that_are_not_complete_are_counted(tmp_path):
    mkts = worlds_markets()
    snap, rr = build(tmp_path, mkts, ks=[k for k in range(N) if k != 2])
    d = snap / "partial"
    d.mkdir()
    (d / "manifest.json").write_text(json.dumps({"state": "running", "started_utc": iso(tcap(2)), "capture_id": "partial"}))
    info = m3.discover_all(snap, 0.0, 4.1e9, window_start=WS)
    assert info["notes"]["pre_window_manifest_not_complete"] == 1 and all(c["id"] != "partial" for c in info["caps"])
    st = tmp_path / "research_lab" / "m3_ch274_dryrun"
    run(snap, rr, st)
    log = [json.loads(x) for x in (st / "logs" / "j1_runs.jsonl").read_text().splitlines()]
    assert m3.slot_of(tcap(2).timestamp())[0] in {d_["slot"] for d_ in statuses(st).values() if d_["kind"] == "missing_capture"}
    assert log[-1]["counts"].get("missing_lookback_slot", 0) >= 1
    # a no-capture root is never mistaken for "every slot missing"
    empty = tmp_path / "empty" / "research_lab" / "snapshots"
    empty.mkdir(parents=True)
    st3 = tmp_path / "research_lab3" / "m3_ch274_dryrun"
    rec = run(empty, None, st3)
    assert rec["missing_slots"] == 0 and rec["processed_slots"] == 0


# --- the remaining funnel classes and the guards ------------------------------------------------------------------------------------------------

def run_small(tmp_path, mkts, **kw):
    snap, rr = build(tmp_path, mkts, rules=False)
    st = tmp_path / "research_lab" / "m3_ch274_dryrun"
    run(snap, rr, st, **kw)
    return st


def test_candidate_classes_first_window_capture_missing_row_age_clock_and_left_censored_in_window(tmp_path):
    g = [(0, ("0.91", "0.93")), (4, ("0.95", "0.96"))]
    h = [(0, ("0.91", "0.93")), (7, ("0.95", "0.96"))]
    mm = {
        1: mk(px=g, event="e1"),  # newly near at the first window capture k = 4, whose k - 1 (3) is before the window
        2: mk(px=h, event="e2", present=[(0, 5), (7, 99)]),  # seen before, no row at k - 1 = 6
        3: mk(px=h, event="e3", present=[(7, 99)]),  # first row at k = 7, already near: left censored, in the window
        4: mk(px=h, event="e4", created=""),  # created_at missing
        5: mk(px=h, event="e5", created="2026-10-21T00:00:00Z"),  # created after k
        6: mk(px=h, event="e6"),  # a plain unit
    }
    st = run_small(tmp_path, mm)
    f = funnel_totals(st)
    c = counts_totals(st)
    assert f["k_minus_1_before_window"] == 1 and f["no_k_minus_1_row"] == 1 and f["left_censored_first_row"] == 1 and c["left_censored_first_row:in_window"] == 1
    assert f["created_at_missing"] == 1 and f["created_at_after_k"] == 1 and f["unit"] == 1
    assert [u["market_id"] for u in read_units(st)] == [6]


def test_guard_classes_prior_unit_and_near_seen_but_candidate(tmp_path):
    mm = {1: mk(event="e1"), 2: mk(event="e2")}
    snap, rr = build(tmp_path, mm, rules=False)
    info = m3.discover_all(snap, 0.0, 4.1e9)
    mp = m3.M3Pass(window_start=WS, window_end=WE, dry_run=True)
    for c in info["caps"][:7]:
        mp.feed(c)
    mp.unit_meta[1] = ["YES", 0, "x"]  # a unit already recorded for market 1 (expected never to happen)
    real_scan = mp._scan

    def scan_then_mark(cap, **kw):
        sc = real_scan(cap, **kw)
        if 2 in sc["cand"]:
            mp.near_seen.add(2)  # a candidate that is also in the near-seen set (expected never to happen)
        return sc

    mp._scan = scan_then_mark
    mp.feed(info["caps"][7])
    assert mp.funnel["prior_unit"] == 1 and mp.funnel["near_seen_but_candidate"] == 1 and mp.funnel["unit"] == 0


def test_sub_counts_of_k_minus_1_not_two_sided(tmp_path):
    h = [(0, ("0.91", "0.93"))]
    mm = {1: mk(px=[*h, (6, ("0.97", "0.95")), (7, ("0.95", "0.96"))], event="e1"), 2: mk(px=[*h, (6, ("x", "y")), (7, ("0.95", "0.96"))], event="e2"),
          3: mk(px=[*h, (6, ("", "0.93")), (7, ("0.95", "0.96"))], event="e3")}
    st = run_small(tmp_path, mm)
    c = counts_totals(st)
    assert c["k_minus_1_not_two_sided:crossed"] == 1 and c["k_minus_1_not_two_sided:unparseable"] == 1 and c["k_minus_1_not_two_sided:one_sided"] == 1 and funnel_totals(st)["k_minus_1_not_two_sided"] == 3
    assert read_units(st) == []


def test_side_counts_exclude_markets_in_the_near_seen_set(tmp_path):
    mm = {1: mk(px=[(0, ("0.50", "0.52")), (7, ("0.95", "0.96")), (9, ("0.97", "0.95"))]), 2: mk(px=[(0, ("0.50", "0.52")), (9, ("0.97", "0.95"))])}
    st = run_small(tmp_path, mm)
    ss = statuses(st)
    assert ss[f"{cid(10)}.json"]["counts"]["crossed_book"] == 1  # market 2 only: market 1 is a unit, in the near-seen set, and its later row is not read
    assert ss[f"{cid(8)}.json"]["counts"]["crossed_book"] == 0


def test_counted_missingness_reaches_the_status_files(tmp_path):
    mkts = worlds_markets()
    snap, rr = build(tmp_path, mkts)
    (snap / cid(9) / "rows_ext.csv.gz").unlink()
    st = tmp_path / "research_lab" / "m3_ch274_dryrun"
    run(snap, rr, st)
    ss = statuses(st)
    assert ss[f"{cid(9)}.json"]["notes"] == {"captures_without_sidecar": 1}
    assert ss[f"{cid(8)}.json"]["notes"] == {}
    assert sum(d["counts"].get("t_d_source:receipt", 0) for d in ss.values() if d["kind"] == "processed") == len(read_units(st))
    assert all("units" in d for d in ss.values() if d["kind"] == "processed")
