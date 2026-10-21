# ruff: noqa: E501
"""LT5 (LIVE_TESTS_5.md) first code unit: vendored-code provenance, the unit builders of J, F, O, H and R, the counts-only
sealed censuses (end to end on a synthetic host tree, and refusal on tampering), O's block (circular-shift) gate and the
size check's scenario-to-test map. Synthetic data only; no network; no outcome or price after an origin is read."""

from __future__ import annotations

import ast
import hashlib
import json
import math
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import live_tests3 as l3
from astrolabe.research_lab import live_tests4 as l4
from astrolabe.research_lab import live_tests5 as lt
from astrolabe.research_lab import live_tests5_analysis as la
from astrolabe.research_lab import live_tests5_base as b

HERE = Path(lt.__file__).resolve().parent
G0 = datetime(2027, 1, 1, 0, 31, tzinfo=UTC)  # slot 0 on the spec grid
CENSUS_DAY = "2027-01-09"  # slots 96 .. 107; H's look-back starts at slot 0
N_MKT = 30


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _spec(tmp_path: Path | None = None, **over) -> dict:
    spec = lt.load_spec(sha=None)
    for k, v in over.items():
        spec[k] = v
    return spec


# --- vendored code -------------------------------------------------------------------------------------------------------


def _segment(text: str, name: str) -> str:
    tree = ast.parse(text)
    node = next(n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == name)
    return ast.get_source_segment(text, node)


def test_vendored_provenance():
    """Every vendored name equals its source up to the module prefixes; when the source file is unchanged since the copy,
    the current source still hashes to the recorded value (R1 ruling 9)."""
    pre = re.compile(r"\b(?:l3|la3|lt|l4|la4)\.")
    base_text = (HERE / "live_tests5_base.py").read_text()
    assert len(b.VENDORED) >= 50
    for name, pv in b.VENDORED.items():
        mine = _segment(base_text, name)
        assert hashlib.sha256(pre.sub("", mine).encode()).hexdigest() == pv["normalised_sha256"], name
        src_text = (HERE / pv["source"]).read_text()
        if hashlib.sha256(src_text.encode()).hexdigest() == pv["source_sha256"]:
            assert hashlib.sha256(pre.sub("", _segment(src_text, name)).encode()).hexdigest() == pv["normalised_sha256"], name


def test_vendored_constants_equal_sources():
    assert b.SNAP_COLS == l3.SNAP_COLS and b.EXT_COLS == l3.EXT_COLS and b.SWEEP_COLS == l4.SWEEP_COLS
    assert b.GRID_S == l3.GRID_S and b.SLOT_TOL_S == l3.SLOT_TOL_S


def test_lt5_code_does_not_import_lt3_lt4():
    for fn in ("live_tests5.py", "live_tests5_analysis.py", "live_tests5_base.py"):
        txt = (HERE / fn).read_text()
        assert not re.search(r"import live_tests[34]|from \. import live_tests[34]|live_tests[34] as", txt), fn


def test_spec_dates_and_scenarios():
    spec = lt.load_spec(sha=None)
    assert spec["registered_utc"] == lt.REGISTERED_UTC and lt.epoch(lt.REGISTERED_UTC) % 86400 == 0
    assert spec["size_check"]["seed"] == 20261147 and spec["size_check"]["worlds"] == 2000
    names = list(la.scenario_table(np.random.default_rng(0), 9).keys())
    assert names == list(spec["size_check"]["scenarios"].keys()) and len(names) == 12
    assert set(lt.CODE_FILES) == {"live_tests5.py", "live_tests5_analysis.py", "live_tests5_base.py", "bounce_decomp.py"}
    bad = dict(json.loads(lt.SPEC_PATH.read_text()), registered_utc="2026-10-31T00:00:00Z")
    p = Path(__import__("tempfile").mkdtemp()) / "s.json"
    p.write_text(json.dumps(bad))
    with pytest.raises(RuntimeError):
        lt.load_spec(p, sha=None)


# --- J -------------------------------------------------------------------------------------------------------------------------


def _trades(mkt: str, rows: list[tuple[float, float, int]]) -> pd.DataFrame:
    return pd.DataFrame({"market_id": mkt, "ts": [r[0] for r in rows], "side": "BUY", "price": [str(r[1]) for r in rows], "size": 10.0,
                         "outcome_index": [r[2] for r in rows], "asset": "a"})


def test_path_fields_snapping_classes_and_causality():
    spec = _spec()
    u = pd.DataFrame({"market_id": ["A", "B", "C"], "t_k": [10_000.0] * 3, "t_p": [2_800.0] * 3, "tick": [0.01] * 3,
                      "steps": [3.0, 4.0, 3.0], "x": [0.03, 0.04, 0.03]})
    tr = pd.concat([
        # A: three prints at one level (0.5003 snaps to 0.50) and one on outcome 1 at 0.50 -> YES 0.50: a jump (levels 1)
        _trades("A", [(3000, 0.50, 0), (4000, 0.5003, 0), (5000, 0.50, 1), (9999, 0.55, 0), (10_000, 0.90, 0), (12_000, 0.10, 0)]),
        # B: four levels for four steps: a grind; C: two levels for three steps: interior
        _trades("B", [(3000, 0.40, 0), (4000, 0.41, 0), (5000, 0.42, 0), (6000, 0.43, 0)]),
        _trades("C", [(3000, 0.40, 0), (4000, 0.41, 0), (100, 0.2, 0)]),
    ])
    r = lt.path_fields(tr, u, np.array([6, 4, 3]), None, spec)
    assert r["n_int"].tolist() == [4, 4, 2]  # A: the 0.55 print at 9999 counts, rows at or after t_k never do
    assert r["levels"].tolist() == [2, 4, 2]
    assert r["cls_j"].tolist() == ["interior", "grind", "interior"]
    assert r.loc[1, "g_path"] == pytest.approx(0.75)
    assert r.loc[0, "age"] == pytest.approx(1.0) and r.loc[0, "fresh"] == 1
    # tick snapping: an off-grid aggregated print never adds a level
    u2 = u.iloc[[0]].assign(steps=3.0)
    tr2 = _trades("A", [(3000, 0.50, 0), (4000, 0.5004, 0), (5000, 0.4997, 0)])
    r2 = lt.path_fields(tr2, u2, np.array([3]), None, spec)
    assert r2.loc[0, "levels"] == 1 and r2.loc[0, "cls_j"] == "jump"


def test_path_interval_truncation():
    spec = _spec()
    u = pd.DataFrame({"market_id": ["A"], "t_k": [10_000.0], "t_p": [2_800.0], "tick": [0.01], "steps": [3.0], "x": [0.03]})
    tr = _trades("A", [(3000 + i, 0.5, 0) for i in range(5)])
    full = lt.path_fields(tr, u, np.array([500.0]), None, spec)  # page full and oldest row after t_{k-1}: truncated
    notfull = lt.path_fields(tr, u, np.array([5.0]), None, spec)
    assert full.loc[0, "interval_truncated"] == 1 and notfull.loc[0, "interval_truncated"] == 0


# --- F -------------------------------------------------------------------------------------------------------------------------


def _members(rows):
    return pd.DataFrame(rows, columns=["market_id", "event_id", "x", "t_row", "neg_risk", "skey"])


def test_family_hierarchy_guard_and_exclusions():
    spec = _spec()
    mem = _members([
        ("u1", "E1", 0.03, 100.0, 0, "ser"), ("a", "E1", 0.0, 100.0, 0, "ser"), ("b", "E1", 0.0, 101.0, 0, "ser"),
        ("c", "E1", 0.02, 104.0, 0, "ser"), ("d", "E1", 0.03, 106.0, 0, "ser"),  # d received 6 s after u1: dropped by the guard
        ("u2", "N1", 0.04, 200.0, 1, "ser"), ("n1", "N1", -0.02, 200.0, 1, "ser"), ("n2", "N1", -0.02, 200.0, 1, "ser"),
        ("n3", "N1", -0.02, 200.0, 1, "ser"),
        ("s1", "E7", 0.04, 199.0, 0, "ser"), ("s2", "E8", 0.04, 199.0, 0, "ser"), ("s3", "E9", 0.04, 199.0, 0, "ser"),
    ])
    units = mem[mem["market_id"].isin(["u1", "u2"])].reset_index(drop=True)
    fs = lt.family_stats(units, mem, spec)
    r1, r2 = fs.iloc[0], fs.iloc[1]
    assert r1["level"] == "event" and r1["n_sib"] == 3  # zero movers are members; d is guarded out
    assert r1["xbar"] == pytest.approx(0.02 / 3) and r1["share_moving"] == pytest.approx(1 / 3)
    assert r1["t_dec"] == pytest.approx(104.0)
    # u2 is neg-risk: never the event level; the series mean excludes its own neg-risk siblings n1..n3
    assert r2["level"] == "series"
    sib = mem[(mem["skey"] == "ser") & (mem["market_id"] != "u2") & (mem["event_id"] != "N1") & (mem["t_row"] <= 205.0)]
    assert r2["n_sib"] == len(sib) and r2["xbar"] == pytest.approx(sib["x"].mean())
    cls = lt.family_classes(np.array([0.03, 0.04, 0.04]), np.array([0.005, 0.035, -0.005]), spec)
    assert cls.tolist() == ["idio", "common", "idio"]


def test_family_guard_loss_recorded():
    spec = _spec()
    mem = _members([("u", "E1", 0.03, 100.0, 0, "event:E1"), ("a", "E1", 0.0, 110.0, 0, "event:E1"),
                    ("b", "E1", 0.0, 110.0, 0, "event:E1"), ("c", "E1", 0.0, 110.0, 0, "event:E1")])
    fs = lt.family_stats(mem.iloc[[0]].reset_index(drop=True), mem, spec)
    assert fs.loc[0, "level"] == "" and fs.loc[0, "reason"] == "guard_loss" and fs.loc[0, "guard_loss"] == 1


# --- O -------------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("mid,yes_tok,expect", [(0.60, True, +1), (0.40, True, -1), (0.40, False, -1), (0.60, False, +1)])
def test_overhang_sign_quadrants(mid, yes_tok, expect):
    """O = |g| m: positive whenever the YES token dominates, negative when the NO token dominates, whatever the sign of g
    (section 7.1). The round's G = g m flips with g."""
    spec = _spec()
    u = pd.DataFrame({"market_id": ["A"], "t_k": [100_000.0], "mid": [mid]})
    rows = [(100_000 - 3600 * i, 0.50 if yes_tok else 0.50, 0 if yes_tok else 1) for i in range(1, 11)]
    tr = _trades("A", rows)
    r = lt.overhang_fields(tr, u, np.array([10]), None, spec).iloc[0]
    yes_side = 1 if yes_tok else -1
    assert np.sign(r["O"]) == yes_side and r["m"] == pytest.approx(yes_side)
    assert np.sign(r["G"]) == np.sign(mid - 0.5) * yes_side and r["vwap"] == pytest.approx(0.5)
    assert expect in (1, -1)


def test_overhang_window_coverage_and_causality():
    spec = _spec()
    u = pd.DataFrame({"market_id": ["A"], "t_k": [100_000.0], "mid": [0.6]})
    tr = _trades("A", [(100_000 - 10 * i, 0.5, 0) for i in range(1, 11)] + [(100_000, 0.99, 0), (100_050, 0.99, 0)])
    r = lt.overhang_fields(tr, u, np.array([500]), None, spec).iloc[0]
    assert r["n24"] == 10 and r["vwap"] == pytest.approx(0.5) and r["trunc24"] == 1  # full page not reaching t - 24 h
    r2 = lt.overhang_fields(tr, u, np.array([12]), None, spec).iloc[0]
    assert r2["trunc24"] == 0


# --- H -------------------------------------------------------------------------------------------------------------------------


def test_window_marks_and_classes():
    spec = _spec()
    M = np.full((3, 90), np.nan)
    M[0, :] = 0.60
    M[0, 10] = 0.70  # the high, 79 slots before column 89
    M[1, :] = 0.50 + 0.10 * np.sin(np.arange(90) / 4.0)
    M[2, :50] = 0.5  # too few present slots in the window
    w = lt.window_marks(M, 89, 84)
    assert w["hi"][0] == pytest.approx(0.70) and w["age_hi"][0] == 79 and w["present"][0] == 84
    assert w["present"][2] < 72
    cls, s = lt.mark_classes(np.array([0.69, 0.50]), {k: w[k][:2] for k in ("hi", "lo", "age_hi", "age_lo")}, spec)
    assert cls[0] == "near_high" and s[0] == 1.0 and cls[1] == "far"
    cls2, _ = lt.mark_classes(np.array([0.71]), {"hi": np.array([0.70]), "lo": np.array([0.6]), "age_hi": np.array([50.0]), "age_lo": np.array([5.0])}, spec)
    assert cls2[0] == "new_extreme"


def test_day_origin_rule():
    spec = _spec()
    k0 = b.slot_of(lt.epoch("2026-10-20T00:31:00Z"), spec)
    assert lt.is_day_origin(k0, spec) and not lt.is_day_origin(k0 + 1, spec) and lt.is_day_origin(k0 + 12, spec)


def test_mid_matrix_spread_rule():
    ser = pd.DataFrame({"bid": [0.40, 0.30], "ask": [0.42, 0.45], "spread": [0.02, 0.15]}, index=["a", "b"])
    ids, M = lt.mid_matrix({0: ser}, [0], 0.10)
    assert list(ids) == ["a", "b"] and M[0, 0] == pytest.approx(0.41) and np.isnan(M[1, 0])


# --- R -------------------------------------------------------------------------------------------------------------------------


def _ser(rows):
    df = pd.DataFrame(rows).set_index("market_id")
    return df


def test_rule_units_fold_donut_inside_and_reward():
    spec = _spec()
    base = {"event_id": "E", "skey": "event:E", "sports": 0, "t_row": 0.0, "end_ts": np.nan, "tick": 0.01, "liq": 1e5,
            "rew_min": 50.0, "rew_maxspread": 3.5}
    ser = _ser([{**base, "market_id": m, "rew_rate": r} for m, r in
                (("in", 10.0), ("cut", 10.0), ("donut", 10.0), ("out", 10.0), ("low", 10.0), ("unrew", 0.0), ("unknown", np.nan))])
    mids = {"in": 0.88, "cut": 0.90, "donut": 0.903, "out": 0.93, "low": 0.12, "unrew": 0.88, "unknown": 0.88}

    def sw(dd):
        return pd.DataFrame({"sbid": [mids[m] - 0.01 for m in mids], "sask": [mids[m] + 0.01 for m in mids], "s_t": 1.0, "s_two": 1,
                             "dbid1": 10.0, "dask1": 10.0 + dd, "dbid5": 100.0, "dask5": 50.0 + dd}, index=list(mids))

    u, cnt = lt.rule_units(ser, ser, sw(0.0), sw(5.0), spec)
    got = dict(zip(u["market_id"], zip(u["inside"], u["rewarded"], strict=True), strict=True))
    assert "donut" not in got and "cut" not in got and "unknown" not in got and cnt["reward_unknown"] == 1  # 0.90 sits in the donut
    assert got["in"] == (1, 1.0) and got["out"] == (0, 1.0) and got["low"] == (1, 1.0) and got["unrew"] == (1, 0.0)
    assert u.loc[u["market_id"] == "low", "f"].iloc[0] == pytest.approx(0.88)
    u2, cnt2 = lt.rule_units(ser, ser, sw(0.0), sw(0.0), spec)  # nothing changed since pass k - 1: dormant
    assert len(u2) == 0 and cnt2["dormant"] == len(u)
    assert lt.imbalance([100.0], [50.0])[0] == pytest.approx(1 / 3)
    nod = dict(spec, r=dict(spec["r"], donut=0.0))  # without the donut, 0.90 exactly is inside (CB6-R's convention)
    u3, _ = lt.rule_units(ser, ser, sw(0.0), sw(5.0), nod)
    assert u3.loc[u3["market_id"] == "cut", "inside"].iloc[0] == 1


# --- gates ---------------------------------------------------------------------------------------------------------------------


def test_offset_range_and_circular_shift():
    assert la.offset_range(8) == (4, 4) and la.offset_range(16) == (4, 12) and la.offset_range(40) == (10, 30)
    codes = np.array([0] * 20 + [1] * 10)
    order = np.r_[np.arange(20)[::-1], np.arange(10)].astype(float)
    plan = la.shift_plan(codes, order, 16)
    assert len(plan) == 1 and list(plan[0]) == list(range(19, -1, -1))
    e = np.arange(30, dtype=float)
    ep = la.circular_shift(e, plan, np.random.default_rng(0))
    assert sorted(ep[:20]) == sorted(e[:20]) and (ep[20:] == e[20:]).all() and not (ep[:20] == e[:20]).all()


def test_block_gate_detects_planted_effect_and_holds_on_null():
    rng = np.random.default_rng(3)
    df, y = la.sim_o_world(rng, rho=0.6)
    r0 = la.block_fl_gate(df, y, "z", ["c1"], sign=+1, draws=99, seed=1)
    assert r0["testable"] and 0 < r0["share_rows_shifted"] <= 1
    y1 = y + 0.05 * df["z"].to_numpy()
    r1 = la.block_fl_gate(df, y1, "z", ["c1"], sign=+1, draws=99, seed=1)
    assert r1["passes"] and r1["p_perm"] < 0.05


def test_worlds_match_declaration():
    rng = np.random.default_rng(5)
    df, _ = la.sim_markov_ma2_world(rng)
    n = df.groupby("market_id").size()
    assert df["market_id"].nunique() == 60 and n.min() >= 6 and n.max() <= 60
    h, _ = la.sim_h_world(rng)
    nh = h.groupby("market_id").size()
    assert h["market_id"].nunique() == 120 and nh.min() >= 4 and nh.max() <= 21 and (h.groupby(["market_id", "day"]).size() == 1).all()
    r, _ = la.sim_r_world(rng)
    assert r["market_id"].nunique() == 100 and r["rf"].between(-0.0601, 0.0591).all()
    flips = r.groupby("market_id")["inside"].nunique()
    assert (flips == 1).mean() > 0.5  # inside is near-constant within most markets
    o, _ = la.sim_o_world(rng, rho=0.95)
    assert o["market_id"].nunique() == 80 and abs(np.corrcoef(o["z"] - o.groupby("market_id")["z"].transform("mean"), o["c1"] - o.groupby("market_id")["c1"].transform("mean"))[0, 1] - 0.85) < 0.1


def test_size_check_maps_failures_to_tests_only(monkeypatch):
    calls = {"s01_fl_binary_iid": lambda: True, "s09_block_o_rho0": lambda: False}
    monkeypatch.setattr(la, "scenario_table", lambda rng, draws: calls)
    r = la.size_check(worlds=20, draws=9, seed=1, binding={"s01_fl_binary_iid": ["J", "F"], "s09_block_o_rho0": ["O"]})
    assert r["se_check_failed_size_scenario"] == ["F", "J"] and not r["all_ok"]
    assert r["scenarios"]["s09_block_o_rho0"]["ok"] and not r["scenarios"]["s01_fl_binary_iid"]["ok"]


def test_size_check_small_run_all_scenarios():
    r = la.size_check(worlds=2, draws=9, seed=11)
    assert len(r["scenarios"]) == 12 and set(r["code_sha256"]) == set(lt.CODE_FILES)
    assert r["scenarios"]["s12_block_o_rho0.95"]["binding_for"] == ["O"]


def test_mde_helpers():
    a = {"t_sum": 3.388, "day_factor": 1.5}
    m = lt.mde_class(10_000, 10_000, 0.04, 3.0, a)
    assert m == pytest.approx(3.388 * 0.04 * math.sqrt(2 / 10_000) * math.sqrt(3) * 1.5)
    assert lt.mde_class(0, 5, 0.04, 3.0, a) == float("inf")
    assert lt.mde_slope_design(100.0, 10.5, 0.05, 4.0, a) == pytest.approx(3.388 * 0.05 / math.sqrt(1050) * 2 * 1.5)


# --- end-to-end censuses on a synthetic host tree -------------------------------------------------------------------------------


def _q(m: int, k: int) -> tuple[float, float, float, float]:
    """(bid, ask, last trade, volume24hr) of market m at slot k."""
    if m == 15:  # H: a high of 0.70 at slot 40, mostly 0.60-0.64, near the high at the census origins
        mid = 0.70 if k == 40 else (0.69 if k in (96, 108) else 0.62 + 0.02 * round(math.sin(k / 5.0), 0))
    elif m == 16:  # H: far from both marks at the origins
        mid = 0.50 if k in (96, 108) else round(0.5 + 0.10 * math.sin(k / 4.0), 2)
    elif 17 <= m <= 21:  # R: folded mids around 0.90
        mid = {17: 0.87, 18: 0.88, 19: 0.92, 20: 0.93, 21: 0.88}[m]
    else:
        mid = round(0.40 + 0.005 * m + 0.12 * math.sin(k / 3.0 + m), 2)
    traded = (k + m) % 3 == 0
    return round(mid - 0.01, 3), round(mid + 0.01, 3), round(mid, 3) if traded else round(0.3 + 0.01 * m, 3), 1000.0 + (50.0 * k if traded else 0.0)


def _meta(m: int) -> dict:
    if m < 5:
        return {"event_id": "100", "neg_risk": "False", "series_slugs": "", "fee_type": "politics_fees"}
    if m < 10:
        return {"event_id": "200", "neg_risk": "True", "series_slugs": '["ser-a"]', "fee_type": "politics_fees"}
    if m < 15:
        return {"event_id": str(300 + m), "neg_risk": "False", "series_slugs": '["ser-a"]', "fee_type": "politics_fees"}
    if m >= 22:
        return {"event_id": str(400 + m), "neg_risk": "False", "series_slugs": "", "fee_type": "sports_fees_v3"}
    return {"event_id": str(500 + m), "neg_risk": "False", "series_slugs": "", "fee_type": "politics_fees"}


def write_capture(root: Path, k: int) -> str:
    start = G0 + timedelta(hours=2 * k)
    cid = start.strftime("%Y%m%dT%H%M%SZ") + f"_{k:08x}"
    d = root / cid
    d.mkdir(parents=True)
    rows, exts = [], []
    for m in range(N_MKT):
        bid, ask, ltp, vol = _q(m, k)
        mt = _meta(m)
        rows.append({"received_utc": _iso(start + timedelta(seconds=5 + (m % 5))), "market_id": str(100 + m), "condition_id": f"0xc{m}",
                     "event_id": mt["event_id"], "closed": "False", "active": "True", "binary": 1, "best_bid": bid, "best_ask": ask,
                     "spread": round(ask - bid, 4), "last_trade_price": ltp, "chg_1h": 0.0, "chg_1d": 0.01, "chg_1w": 0.0, "liquidity": 2e5,
                     "volume24hr": vol, "end_date": _iso(start + timedelta(days=30)), "clob_token_id_0": f"tok{m}", "neg_risk": mt["neg_risk"]})
        rew = json.dumps([{"rewardsDailyRate": 10.0, "startDate": "2026-01-01", "endDate": "2027-12-31"}]) if 17 <= m <= 20 else "[]"
        exts.append({"market_id": str(100 + m), "fee_type": mt["fee_type"], "fee_category": "", "fees_enabled": "1", "fee_schedule": "",
                     "order_price_min_tick_size": "0.01", "created_at": _iso(G0 - timedelta(days=30)), "series_slugs": mt["series_slugs"],
                     "rewards_min_size": "50", "rewards_max_spread": "3.5", "clob_rewards": rew})
    pd.DataFrame(rows).to_csv(d / "rows.csv.gz", index=False, compression="gzip")
    pd.DataFrame(exts).to_csv(d / "rows_ext.csv.gz", index=False, compression="gzip")
    (d / "manifest.json").write_text(json.dumps({"capture_id": cid, "state": "complete", "started_utc": _iso(start)}))
    return cid


def write_sweep(root: Path, cid: str, k: int) -> None:
    start = G0 + timedelta(hours=2 * k, minutes=8)
    d = root / (start.strftime("%Y%m%dT%H%M%SZ") + f"_s{k:07x}")
    d.mkdir(parents=True)
    rows = []
    for m in range(N_MKT):
        bid, ask, _, _ = _q(m, k)
        rows.append({"token_id": f"tok{m}", "market_id": str(100 + m), "batch_receipt_utc": _iso(start), "best_bid": bid, "best_ask": ask,
                     "state": "two_sided", "bid_size_1": 60.0, "ask_size_1": 40.0, "depth_bid_1c": 60.0 + (k * m) % 7, "depth_ask_1c": 40.0,
                     "depth_bid_5c": 200.0 + 10 * ((k + m) % 9), "depth_ask_5c": 120.0, "min_order_size": 5.0})
    pd.DataFrame(rows).to_csv(d / "rows.csv.gz", index=False, compression="gzip")
    (d / "manifest.json").write_text(json.dumps({"state": "complete", "series_index": 0, "snapshot_id": cid}))


def write_sample(root: Path, cid: str, k: int) -> str:
    start = G0 + timedelta(hours=2 * k, minutes=10)
    sid = start.strftime("%Y%m%dT%H%M%SZ") + f"_t{k:07x}"
    d = root / sid
    d.mkdir(parents=True)
    feats, trades = [], []
    for m in range(N_MKT):
        o = (G0 + timedelta(hours=2 * k, seconds=5 + (m % 5))).timestamp()
        bp, ap, _, _ = _q(m, k - 1)
        bk, ak, _, _ = _q(m, k)
        lo, hi = sorted(((bp + ap) / 2, (bk + ak) / 2))
        for i in range(12):
            p = round(lo + (hi - lo) * (i % 4) / 3.0, 3) if m % 2 else round(hi, 3)
            trades.append({"market_id": str(100 + m), "ts": int(o - 600 - 500 * i), "side": "BUY" if i % 3 else "SELL", "price": p, "size": 5.0 + i,
                           "outcome_index": i % 2 if m % 4 == 0 else 0, "asset": f"tok{m}"})
        for i in range(10):
            trades.append({"market_id": str(100 + m), "ts": int(o - 7200 * 2 - 3000 * i), "side": "BUY", "price": 0.3, "size": 3.0,
                           "outcome_index": 0, "asset": f"tok{m}"})
        trades.append({"market_id": str(100 + m), "ts": int(o + 30), "side": "BUY", "price": 0.99, "size": 1.0, "outcome_index": 0, "asset": f"tok{m}"})
        feats.append({"market_id": str(100 + m), "status": "ok", "origin_utc": _iso(datetime.fromtimestamp(o, UTC)), "n_returned": 23})
    pd.DataFrame(feats).to_csv(d / "features.csv.gz", index=False, compression="gzip")
    pd.DataFrame(trades).to_csv(d / "trades.csv.gz", index=False, compression="gzip")
    (d / "plan.json").write_text(json.dumps({"snapshot_id": cid}))
    (d / "manifest.json").write_text(json.dumps({"state": "complete", "frame": "active", "snapshot_id": cid}))
    return sid


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("lt5world")
    snap, sw, smp = tmp / "snap", tmp / "sweeps", tmp / "samples"
    ids = {k: write_capture(snap, k) for k in range(0, 109)}
    for k in range(95, 109):
        write_sweep(sw, ids[k], k)
    samples = [write_sample(smp, ids[k], k) for k in (100, 101)]
    files = {}
    for d in [*snap.iterdir(), *sw.iterdir()]:
        sub = "snapshots" if d.parent == snap else "book_sweeps"
        for fn in ("rows.csv.gz", "rows_ext.csv.gz", "manifest.json"):
            if (d / fn).exists():
                files[f"data-dumps/research_lab/{sub}/{d.name}/{fn}"] = {"sha256": lt.sha256_file(d / fn)}
    (tmp / "cseal.json").write_text(json.dumps({"files": files}))
    sfiles = {f"data-dumps/research_lab/trade_samples/{s}/{fn}": {"sha256": lt.sha256_file(smp / s / fn)}
              for s in samples for fn in ("features.csv.gz", "manifest.json", "plan.json", "trades.csv.gz")}
    (tmp / "sseal.json").write_text(json.dumps({"samples": samples, "files": sfiles}))
    return {"tmp": tmp, "snap": snap, "sweeps": sw, "samples": smp, "ids": ids, "sids": samples}


def test_census_captures_end_to_end_counts_only(world, tmp_path):
    w = world
    res = lt.census_captures(seal=w["tmp"] / "cseal.json", snapshot_root=w["snap"], sweep_root=w["sweeps"], work=tmp_path / "work",
                             days=[CENSUS_DAY], spec=_spec())
    assert "error" not in res and res["inputs_verified"] and len(res["captures"]) == 12
    f, h, r = res["CF5"], res["CHW"], res["CRW"]
    assert f["formed"] > 0 and set(f["by_level"]) <= {"event", "series"} and "pass" in f["gate_F"]
    assert f["design_effect_family"]["DE_gate"] >= 3.0
    assert h["by_class"].get("near_high", 0) >= 1 and h["by_class"].get("far", 0) >= 1 and "pass" in h["gate_H"]
    assert r["rewarded_inside_21d"] > 0 and r["rewarded_outside_21d"] > 0 and r["depth_band"] == "5c" and "pass" in r["gate_R"]
    assert not list((tmp_path / "work").glob("**/outcomes/*"))  # no target is ever written


def test_census_captures_refuses_tampered_input(world, tmp_path):
    w = world
    seal = json.loads((w["tmp"] / "cseal.json").read_text())
    key = next(k for k in seal["files"] if k.endswith("rows_ext.csv.gz"))
    seal["files"][key]["sha256"] = "0" * 64
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(seal))
    res = lt.census_captures(seal=p, snapshot_root=w["snap"], sweep_root=w["sweeps"], work=tmp_path / "w2", days=[CENSUS_DAY], spec=_spec())
    assert "error" in res and any(x["file"] == key for x in res["bad"])


def test_census_flow_end_to_end(world, tmp_path):
    w = world
    res = lt.census_flow(seal=w["tmp"] / "sseal.json", capture_seal=w["tmp"] / "cseal.json", sample_roots=[w["samples"]], snapshot_root=w["snap"],
                         work=tmp_path / "wf", spec=_spec())
    assert "error" not in res and res["samples"] == 2
    cj, co = res["CJ"], res["CO"]
    assert "gate_J" in cj and "gate_O" in co
    assert cj["qualifying"] > 0 and cj["jump_share"] > 0 and cj["grind_share"] > 0 and cj["interval_truncated_share"] == 0.0
    assert co.get("covered", 0) > 0 and np.isfinite(co["zO"]["scale_c"])
    tampered = json.loads((w["tmp"] / "sseal.json").read_text())
    tampered["files"][next(iter(tampered["files"]))]["sha256"] = "1" * 64
    p = tmp_path / "s2.json"
    p.write_text(json.dumps(tampered))
    res2 = lt.census_flow(seal=p, capture_seal=w["tmp"] / "cseal.json", sample_roots=[w["samples"]], snapshot_root=w["snap"], work=tmp_path / "wf2", spec=_spec())
    assert "error" in res2


def test_runner_refuses_overwrite_and_cap(tmp_path, monkeypatch):
    import importlib.util

    spec_ = importlib.util.spec_from_file_location("run_lt5", Path(lt.ROOT) / "backend" / "scripts" / "run_live_tests5.py")
    mod = importlib.util.module_from_spec(spec_)
    spec_.loader.exec_module(mod)
    out = tmp_path / "o.json"
    out.write_text("x")
    assert mod.main(["size-check", "--worlds", "1", "--draws", "3", "--out", str(out)]) == 1
    monkeypatch.setattr(mod, "_cap", lambda gb: True)
    assert mod.main(["census-flow", "--sample-root", str(tmp_path), "--work", str(tmp_path / "w"), "--data-dumps-cap-gb", "1"]) == lt.TEMPFAIL
