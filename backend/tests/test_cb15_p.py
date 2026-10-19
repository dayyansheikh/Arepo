# ruff: noqa: E501
"""CB15-P tests (docs/research_lab/CREATIVE_BATCH_15.md CB15-P, sections 1.3, 2.1-2.6, 5): offline fixtures only; no network; no real CB15 quantity."""

from __future__ import annotations

import json
import math
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from astrolabe.research_lab import cb15_common as c15
from astrolabe.research_lab import cb15_p as p

HOUR = 3600.0
DAY = 86400.0
BASE = p.ep("2025-03-01T00:00:00Z")


# ---- guards ------------------------------------------------------------------------------------------------------------------------------------------


def test_matches_reader_never_reads_p_end(tmp_path):
    mp = tmp_path / "cross_venue" / "matches.json"
    mp.parent.mkdir()
    mp.write_text(json.dumps([{"k_ticker": "K1", "p_end": "2025-05-01", "p_market_id": "1", "p_event_id": "e", "k_open": "2025-01-01T00:00:00Z", "p_start": "x", "score": 0.9}]))
    r = p.read_matches(mp)
    assert set(r["K1"]) == set(p.MATCH_FIELDS) and "p_end" not in r["K1"] and "score" not in r["K1"]
    with pytest.raises(c15.Refused):
        p.read_matches(tmp_path / "cross_venue_live" / "matches.json")


def test_kalshi_result_discarded_and_transactions_hash_free():
    k = p.strip_kalshi({"ticker": "X", "result": "yes", "settlement_value": 100, "open_time": "t"})
    assert "result" not in k and "settlement_value" not in k
    tx = p.transactions([{"timestamp": 10, "price": 0.4, "size": 2, "outcomeIndex": 0, "transactionHash": "h", "side": "BUY", "proxyWallet": "0x"},
                         {"timestamp": 11, "price": 0.7, "size": 2, "outcomeIndex": 1, "transactionHash": "h"}], 0)
    assert len(tx) == 1 and set(tx[0]) == {"ts", "vwap_yes", "min_yes", "max_yes", "size"}
    assert abs(tx[0]["min_yes"] - 0.3) < 1e-12 and abs(tx[0]["max_yes"] - 0.4) < 1e-12 and tx[0]["ts"] == 11


def test_rows_at_hist_end_refused():
    with pytest.raises(c15.Refused):
        p.refuse_hist_row(p.ep(p.T15_HIST_END))
    p.refuse_hist_row(p.ep(p.T15_HIST_END) - 1)


def test_volume_is_opened_only_by_the_screen(tmp_path):
    d = tmp_path / "research_lab" / "history" / "h15_birth"
    c15.write_gz_csv(d / p.DATA_FILES["volume"], p.VOL_COLUMNS, [["1", 5.0]])
    assert p.open_volume(d, "screen-P") == {"1": 5.0}
    with pytest.raises(c15.Refused):
        p.open_volume(d, "census-P")


def test_part_p_stays_undeclared_until_stage2():
    d = c15.rules_part_file_doc("P")
    assert d["part_declared"] is False and "Stage-2" in d["reason"]


# ---- birth and clocks ----------------------------------------------------------------------------------------------------------------------------


def test_birth_from_the_first_transaction_and_history_before_ignored():
    txs = p.transactions([{"timestamp": 1000, "price": 0.3, "size": 1, "outcomeIndex": 0}, {"timestamp": 2000, "price": 0.4, "size": 1, "outcomeIndex": 0}], 0)
    tb, v = p.birth_of(txs, "complete")
    assert tb == 1000 and abs(v - 0.3) < 1e-12
    assert math.isnan(p.birth_of(txs, "uncovered")[0])  # no birth print (uncovered)
    pts = [(900.0, 0.50), (1200.0, 0.33)]
    assert math.isnan(p.ph_at(pts, 1500.0, tb))  # the 1200 point is not usable before 1800
    assert p.ph_at(pts, 1800.0, tb) == 0.33 and p.ph_at([(900.0, 0.5)], 1e6, tb) != p.ph_at([(900.0, 0.5)], 1e6, tb)  # a point before t_birth is never used (nan)
    before, seeded = p.seeded_flags(pts, tb)
    assert before == 1 and seeded


def test_p_d_is_the_last_print_at_or_before_t_d():
    txs = p.transactions([{"timestamp": 0, "price": 0.3, "size": 1, "outcomeIndex": 0}, {"timestamp": 300, "price": 0.35, "size": 1, "outcomeIndex": 0},
                          {"timestamp": 601, "price": 0.9, "size": 1, "outcomeIndex": 0}], 0)
    assert p.p_at(txs, 600, max_age=math.inf) == 0.35
    assert math.isnan(p.p_at(txs, 600 + 3 * HOUR))  # age > 2 h -> no print


def test_kalshi_mid_age_and_spread():
    kc = np.array([[1000.0, 0.40, 0.46], [2000.0, 0.40, 0.55]])
    assert abs(p.k_mid_at(kc, 1500.0) - 0.43) < 1e-12
    assert math.isnan(p.k_mid_at(kc, 2100.0))  # spread 15c
    assert math.isnan(p.k_mid_at(kc[:1], 1000.0 + 3601))  # age > 60 min
    assert math.isnan(p.k_mid_at(kc, 999.0))


def _meta(tb: float, *, lead: float = 48 * HOUR, end: float | None = None, kt: str = "K", mid: str = "1", ev: str = "e1", cat: str = "Politics") -> dict:
    return {"k_ticker": kt, "p_market_id": mid, "p_event_id": ev, "k_cat": cat, "k_open": tb - lead, "end_sched": end if end is not None else tb + 30 * DAY, "t_birth": tb,
            "t_birth_vwap": 0.4, "fee_rate": "", "c1_win_start": tb + 20 * DAY, "c1_win_end": tb + 30 * DAY, "ph_before_birth": 0, "ph_first_seeded": False, "reach": "complete"}


def test_kalshi_first_at_24h_exactly_and_end_rule():
    tb = BASE
    kc = np.array([[tb + 300.0, 0.5, 0.52]])
    txs = [{"ts": tb, "vwap_yes": 0.4, "min_yes": 0.4, "max_yes": 0.4, "size": 10.0}]
    assert p.unit_features(_meta(tb, lead=24 * HOUR), txs, kc)["label"] == "ok"
    assert p.unit_features(_meta(tb, lead=24 * HOUR - 1), txs, kc)["label"] == "polymarket first (binding)"
    assert p.unit_features(_meta(tb, end=tb + 600 + 25 * HOUR - 1), txs, kc)["label"] == "ends early (scheduled)"
    assert p.unit_features({**_meta(tb), "t_birth": ""}, txs, kc)["label"] == "no birth print (uncovered)"
    late = p.ep(p.T15_HIST_END) - 10 * HOUR
    assert p.unit_features(_meta(late), txs, kc)["label"] == "after T15_hist_end"


def test_history_target_label():
    tb = BASE
    f = {"t_d": tb + 600, "p_d": 0.4, "t_birth": tb}
    txs = [{"ts": tb, "vwap_yes": 0.4, "min_yes": 0.4, "max_yes": 0.4, "size": 1.0}]
    r = p.unit_target(f, txs, [(tb + 600 + 23 * HOUR, 0.5)])
    assert r["history_target"] and abs(r["delta"] - 0.1) < 1e-12
    txs2 = txs + [{"ts": tb + 600 + 23 * HOUR, "vwap_yes": 0.45, "min_yes": 0.45, "max_yes": 0.45, "size": 1.0}]
    r2 = p.unit_target(f, txs2, [])
    assert not r2["history_target"] and abs(r2["delta"] - 0.05) < 1e-12
    assert p.unit_target(f, txs, [])["label"] == "no target"


def test_p2_entry_max_exit_min_stale_no_exit():
    td = BASE
    f = {"t_d": td, "g_d": 0.10}
    tx = [{"ts": td + 120, "vwap_yes": 0.41, "min_yes": 0.40, "max_yes": 0.42, "size": 50.0}, {"ts": td + 600, "vwap_yes": 0.43, "min_yes": 0.43, "max_yes": 0.44, "size": 500.0},
          {"ts": td + 24 * HOUR + 60, "vwap_yes": 0.55, "min_yes": 0.52, "max_yes": 0.56, "size": 5.0}, {"ts": td + 24 * HOUR + 120, "vwap_yes": 0.57, "min_yes": 0.57, "max_yes": 0.57, "size": 5.0}]
    r = p.p2_net(f, tx, 0.04)
    assert r["status"] == "ok" and r["entry"] == 0.44 and r["exit"] == 0.52 and r["size"] == 100.0 and not r["stale"]  # entry max YES, exit min YES
    assert abs(r["net"] - (0.52 - 0.44 - 0.04 * 0.44 * 0.56 - 0.04 * 0.52 * 0.48)) < 1e-12
    rn = p.p2_net({"t_d": td, "g_d": -0.10}, tx, 0.04)
    assert rn["entry"] == pytest.approx(0.60) and rn["exit"] == pytest.approx(1 - 0.57)  # NO: pay 1 - min YES; exit 1 - max YES
    stale = p.p2_net(f, tx[:2] + [{"ts": td + 5 * HOUR, "vwap_yes": 0.5, "min_yes": 0.5, "max_yes": 0.5, "size": 1.0}], 0.04)
    assert stale["stale"] and stale["exit"] == 0.5
    assert p.p2_net(f, tx[:2], 0.04)["status"] == "no exit"
    assert p.p2_net(f, tx[2:], 0.04)["status"] == "no entry print"
    assert p.p2_net({"t_d": td, "g_d": 0.0499}, tx, 0.04)["status"] == "below gap"


# ---- census ------------------------------------------------------------------------------------------------------------------------------------------


def test_birth_census_key_drops_by_source_and_gpb():
    pairs, matches = [], {}
    for i in range(70):
        kt = f"K{i}"
        pairs.append({"k_ticker": kt, "event": f"e{i // 2}", "cat": "Politics", "win_start": 0.0, "win_end": 1.0})
        matches[kt] = {"k_ticker": kt, "k_series": "S", "k_cat": "Sports" if i >= 68 else "Politics", "k_src": "/markets", "k_open": "2025-01-01T00:00:00Z",
                       "p_start": "2025-01-03T00:00:00Z" if i % 7 else "2025-01-01T12:00:00Z", "p_market_id": str(i), "p_event_id": f"e{i // 2}", "k_close": "", "p_token0": ""}
    ksrc = {"market": {"0": {c15.C1_SOURCE}, "1": {c15.C1_SOURCE, "frame:h11_pol"}}, "event": {}, "neg_risk_market": {}, "series": {}}
    rows, rep = p.birth_census(pairs, matches, ksrc)
    ids = {r[4] for r in rows}
    assert "1" not in ids  # a C1 + CB11-P key is dropped
    assert rep["key_drops_by_source"] == {"c1+frame:h11_pol": 1} and rep["sports_excluded"] == 2
    assert "2" in ids and "0" not in ids  # "0" kept by the key rule but Polymarket-first-ish (12 h lead)
    assert rep["kalshi_first_proxy"]["pairs"] == len(rows) and rep["gpb"]["pass"] is False  # < 60 proxy pairs
    assert rep["no_drop_counterfactual"]["pairs"] == len(rows) + 1


def test_c1_frame_asserts_the_reproduction():
    def loader(r):
        prs = [SimpleNamespace(pair_id=f"K{i}", event=f"e{i % 183}", cat="Politics", t=np.array([1.0, 2.0])) for i in range(316)]
        return {"pairs": prs, "report": {"pairs": 316, "events": 183}}

    pairs, _ = p.c1_frame(Path("/x/cross_venue"), loader=loader)
    assert len(pairs) == 316 and pairs[0]["win_start"] == 1.0
    with pytest.raises(c15.Refused):
        p.c1_frame(Path("/x/cross_venue"), loader=lambda r: {"pairs": loader(r)["pairs"][:-1]})


# ---- synthetic data for census and screen --------------------------------------------------------------------------------------------------------------


def _synth(n: int = 80, slope: float = 0.6, later_slope: float = 0.1, seed: int = 3) -> tuple[dict, dict]:
    rng = np.random.default_rng(seed)
    meta, tx, kc, ph, vols = {}, {}, {}, {}, {}
    for i in range(n):
        kt, mid, ev = f"K{i}", str(i), f"e{i // 2}"
        tb = BASE + i * 2 * DAY + 3600
        td = tb + 600
        tl = td + 7 * DAY
        p0 = float(rng.uniform(0.3, 0.7))
        g = float(rng.choice([-1, 1]) * rng.uniform(0.06, 0.2))
        k0 = p0 + g
        target = p0 + slope * g + float(rng.normal(0, 0.01))
        pl = p0 + 0.5 * g
        gl = k0 - pl
        tl_target = pl + later_slope * gl + float(rng.normal(0, 0.01))
        rows = [(tb, 0.5 * p0 + 0.25), (tb + 300, p0), (td + 120, p0 + 0.005), (td + 600, p0), (td + 12 * HOUR + 60, 0.5 * (p0 + target)), (td + 22.5 * HOUR, target),
                (td + 24 * HOUR + 120, target - 0.005),
                (tl - 3600, pl), (tl + 23 * HOUR, tl_target), (tl + 24 * HOUR + 60, tl_target)]
        tx[mid] = [{"ts": t, "vwap_yes": v, "min_yes": v - 0.002, "max_yes": v + 0.002, "size": 200.0} for t, v in rows]
        kc[kt] = np.array([[t, k0 - 0.01, k0 + 0.01] for t in np.arange(tb - 6 * HOUR, td + 25 * HOUR, 600.0)] + [[t, k0 - 0.01, k0 + 0.01] for t in np.arange(tl - HOUR, tl + 25 * HOUR, 600.0)])
        ph[mid] = []
        meta[kt] = {**_meta(tb, kt=kt, mid=mid, ev=ev, cat="Elections" if i % 2 else "Politics", lead=(96 if i % 3 == 0 else 48) * HOUR), "t_birth_vwap": 0.5 * p0 + 0.25}
        vols[mid] = float(rng.uniform(1e4, 1e6))
    return {"meta": meta, "tx": tx, "kc": kc, "ph": ph}, vols


def test_se_only_proxy_returns_only_ses():
    data, _ = _synth(40)
    feats = p.features_table(data)
    out = p.se_only_proxy(feats, data)
    assert set(out) == {"p1", "p2"} and set(out["p1"]) == {"n", "se"} and set(out["p2"]) == {"n", "se"}
    assert out["p1"]["n"] == 40 and math.isfinite(out["p1"]["se"])


def test_census_gates_and_counts_only():
    data, _ = _synth(80)
    c = p.census_p(data)
    assert c["gp"]["P1"]["pass"] and c["gp"]["P2"]["pass"] and c["gpp"]["P1"]["pass"]
    s = json.dumps(c, default=str)
    assert "slope" not in s and "delta" not in s.lower().replace("delta_l", "")
    small, _ = _synth(30)
    c2 = p.census_p(small)
    assert not c2["gp"]["P1"]["pass"] and not c2["gp"]["P2"]["pass"]


def test_tercile_with_14_units_is_unknown():
    vols = {str(i): float(i) for i in range(42)}
    low = p.lowest_tercile(vols, [str(i) for i in range(42)])
    assert len(low) == 14
    data, v2 = _synth(42)
    res = p.p1_test(data, {k: (val if int(k) < 42 else math.nan) for k, val in vols.items()}, draws_placebo=5, boot_draws=50)
    assert res["verdict"] == p.NOT_TESTABLE_POP  # 42 < 60 pairs: the population minimum binds first


def test_screen_advances_on_a_planted_birth_effect(tmp_path):
    data, vols = _synth(80)
    r1 = p.p1_test(data, vols, draws_placebo=20, boot_draws=200)
    assert r1["testable"] and r1["est"] > p.P1_FLOOR and r1["p"] < 0.01, r1
    assert r1["birth_contrast"]["est"] > 0 and r1["checks"]["birth_contrast"], r1["birth_contrast"]
    assert r1["volume_tercile"]["status"] == "ok"
    assert r1["checks"]["floor"] and r1["checks"]["opening_print_control"], r1["checks"]
    assert all(r1["checks"].values()) and r1["advance"], r1["checks"]
    r2 = p.p2_test(data, vols)
    assert r2["testable"] and r2["est"] > p.P2_FLOOR, r2
    assert all(r2["checks"].values()) and r2["advance"], r2["checks"]
    assert r2["worst_case_reach"]["n"] == r2["n"]


def test_screen_null_and_generic_convergence_do_not_advance():
    data, vols = _synth(80, slope=0.6, later_slope=0.8)  # a steeper slope later in life: generic convergence, the birth contrast fails
    r1 = p.p1_test(data, vols, draws_placebo=5, boot_draws=100)
    assert not r1["checks"]["birth_contrast"] and not r1["advance"]
    data0, vols0 = _synth(80, slope=0.0, later_slope=0.0)
    r0 = p.p1_test(data0, vols0, draws_placebo=5, boot_draws=50)
    assert not r0["advance"]


def test_screen_gates_from_census(tmp_path):
    data, vols = _synth(80)
    d = tmp_path / "research_lab" / "history" / "h15_birth"
    rows_meta = [[m.get(c, "") for c in p.META_COLUMNS] for m in data["meta"].values()]
    c15.write_gz_csv(d / p.DATA_FILES["meta"], p.META_COLUMNS, rows_meta)
    c15.write_gz_csv(d / p.DATA_FILES["tx"], p.TX_COLUMNS, [[mid, t["ts"], t["vwap_yes"], t["min_yes"], t["max_yes"], t["size"]] for mid, v in data["tx"].items() for t in v])
    c15.write_gz_csv(d / p.DATA_FILES["kalshi"], p.K_COLUMNS, [[kt, *r] for kt, v in data["kc"].items() for r in v.tolist()])
    c15.write_gz_csv(d / p.DATA_FILES["prices"], p.PH_COLUMNS, [])
    c15.write_gz_csv(d / p.DATA_FILES["volume"], p.VOL_COLUMNS, [[k, v] for k, v in vols.items()])
    census = {"gp": {"P1": {"pass": True}, "P2": {"pass": False}}, "gpp": {"P1": {"pass": False, "mde": 0.7}, "P2": {"pass": True, "mde": 0.01}}}
    res = p.screen_p(d, census, draws_placebo=5, boot_draws=50)
    assert res["P1"]["verdict"] == p.NOT_RUN_POWER and res["P2"]["verdict"] == p.NOT_TESTABLE_POP
    assert p.load_data(d)["meta"]["K0"]["p_market_id"] == "0"
