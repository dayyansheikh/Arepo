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


def test_part_p_is_declared_with_stage2_and_common_e_untouched():
    d = c15.rules_part_file_doc("P")
    assert d["part_declared"] is True and p.part_unready() is None
    assert "import cb15_p" not in Path(c15.__file__).read_text() and "cb15_p as" not in Path(c15.__file__).read_text()  # common does not import P


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


# ---- Stage 2: watcher and rep ------------------------------------------------------------------------------------------------------------------------


NOW = p.ep("2026-11-10T12:00:00Z")


def _gm(i: int, created: float, q: str) -> dict:
    return {"id": str(9000 + i), "outcomes": '["Yes","No"]', "clobTokenIds": json.dumps([f"y{i}", f"n{i}"]), "question": q, "createdAt": p.cm.iso(created), "endDate": "2026-12-31T00:00:00Z",
            "conditionId": f"c{i}", "events": [{"id": f"ev{i}"}], "outcomePrices": '["0.5","0.5"]', "feeSchedule": {"rate": 0.02}}


def _km(t: str, title: str, open_t: float, sub: str = "") -> dict:
    return {"ticker": t, "event_ticker": f"{t.split('-')[0]}-X", "title": title, "yes_sub_title": sub, "close_time": "2026-12-31T00:00:00Z", "open_time": p.cm.iso(open_t), "result": "", "market_type": "binary"}


class LiveLim:
    """Gamma, Data API, CLOB /book and Kalshi fakes, counting requests."""

    def __init__(self, listings, kalshi, trades, cat="Politics"):
        self.listings, self.kalshi, self.trades, self.cat, self.requests = listings, kalshi, trades, cat, 0
        self.book_fail = 0  # the next N /book calls answer 500
        self.kalshi_pages: list | None = None  # paged Kalshi listing: [(markets, cursor)], a None entry = a 500

    def get(self, url, params):
        self.requests += 1
        if url == c15.GAMMA_MARKETS:
            return 200, self.listings if params["offset"] == 0 else []
        if url.endswith("/markets") and "kalshi" in url:
            if self.kalshi_pages is not None:
                i = int(params.get("cursor") or 0)
                pg = self.kalshi_pages[i]
                return (500, None) if pg is None else (200, {"markets": pg, "cursor": str(i + 1) if i + 1 < len(self.kalshi_pages) else ""})
            return 200, {"markets": self.kalshi, "cursor": ""}
        if "/series/" in url:
            return 200, {"series": {"category": self.cat}}
        if url.endswith("/orderbook"):
            return 200, {"orderbook": {"yes_dollars": [["0.55", 10]], "no_dollars": [["0.40", 10]]}}
        if url == p.CLOB_BOOK:
            if self.book_fail > 0:
                self.book_fail -= 1
                return 500, None
            return 200, {"bids": [{"price": "0.49", "size": "50"}], "asks": [{"price": "0.51", "size": "50"}]}
        if "trades" in url:
            return 200, self.trades.get(params["market"], [])
        raise AssertionError(url)


def test_watcher_matches_polls_reads_audits_and_stops(tmp_path):
    hist = tmp_path / "research_lab" / "history"
    q = "Will the Federal Reserve cut rates at the December 2026 meeting"
    lis = [_gm(1, NOW - 600, q)]
    kal = [_km("FED-26DEC", q, NOW - 3 * DAY)]
    lim = LiveLim(lis, kal, {"c1": [{"timestamp": NOW + 60, "price": 0.5, "size": 3, "outcomeIndex": 0, "transactionHash": "h"}]})
    r = p.p_live(hist, lim, lim, now=p.ep(p.T15_P2_START_MIN) - 1, rules_sha="x", freeze_ts=None)
    assert r["status"] == "p_live_idle"
    r = p.p_live(hist, lim, lim, now=NOW, rules_sha="x", freeze_ts=None, clock=lambda: NOW)
    assert r["matched"] == 0  # no Kalshi cache yet: the scan is skipped and logged, nothing is taken
    c = p.p_cache(hist, lim, now=NOW, freeze_ts=None, clock=lambda: NOW)
    assert c["status"] == "p_cache_complete" and c["cached"] == 1
    assert p.p_cache(hist, lim, now=NOW + 60, freeze_ts=None, clock=lambda: NOW + 60)["status"] == "p_cache_fresh"
    r = p.p_live(hist, lim, lim, now=NOW + 30, rules_sha="x", freeze_ts=None, clock=lambda: NOW + 30)
    assert r["matched"] == 1, r
    live = hist / p.LIVE_RUN
    pr = next(c15.jsonl_iter(live / p.LIVE_FILES["pairs"]))
    assert pr["eligible"] and pr["kalshi_first"] and pr["k_cat"] == "Politics" and "result" not in json.dumps(pr)
    r = p.p_live(hist, lim, lim, now=NOW + 120, rules_sha="x", freeze_ts=None, clock=lambda: NOW + 120)
    assert r["births"] == 1  # reads and polls run before the hourly scan: the first poll is on the next minute
    births = list(c15.jsonl_iter(live / p.LIVE_FILES["first_prints"]))
    assert len(births) == 1 and births[0]["t_birth"] == NOW + 60 and not births[0]["late"]
    td = NOW + 60 + 600
    r = p.p_live(hist, lim, lim, now=td + 30, rules_sha="x", freeze_ts=None, clock=lambda: td + 31)
    assert r["reads"] == 1
    r = p.p_live(hist, lim, lim, now=td + DAY + 400, rules_sha="x", freeze_ts=None, clock=lambda: td + DAY + 401)
    assert r["reads"] == 0  # 24-h read window (5 min) missed: unavailable, logged
    gaps = [json.loads(x) for x in (live / p.LIVE_FILES["gaps"]).read_text().splitlines()]
    assert any(g.get("which") == "t_d+24h" for g in gaps)
    later = NOW + 8 * DAY
    p.p_live(hist, lim, lim, now=later, rules_sha="x", freeze_ts=None, clock=lambda: later)
    batch = json.loads((live / p.LIVE_FILES["audit_dir"] / f"{c15.iso_week_of(NOW)}.json").read_text())
    assert batch["blind"] and set(batch["pairs"][0]) == {"pair_id", "k_text", "p_text"}


def test_watcher_excludes_polymarket_first_and_sports(tmp_path):
    hist = tmp_path / "research_lab" / "history"
    q = "Will the Federal Reserve cut rates at the December 2026 meeting"
    lim = LiveLim([_gm(1, NOW - 600, q)], [_km("FED-26DEC", q, NOW - 3 * DAY)], {}, cat="Sports")
    p.p_cache(hist, lim, now=NOW, freeze_ts=None, clock=lambda: NOW)
    p.p_live(hist, lim, lim, now=NOW + 30, rules_sha="x", freeze_ts=None)
    pr = next(c15.jsonl_iter(hist / p.LIVE_RUN / p.LIVE_FILES["pairs"]))
    assert not pr["eligible"]
    mm = p.match_new([p.kalshi_record(_km("FED-26DEC", q, NOW - 3600))], [p.poly_listing(_gm(2, NOW - 600, q))])  # Kalshi opened < 24 h before the listing
    assert len(mm) == 1 and not mm[0]["kalshi_first"]  # matched against the full cache (C1 mutual best), the lead is checked afterwards (P-8)


def test_watcher_closes_at_the_cap(tmp_path):
    hist = tmp_path / "research_lab" / "history"
    lim = LiveLim([], [], {})
    r = p.p_live(hist, lim, lim, now=p.ep(p.T15_P2_CAP), rules_sha="x", freeze_ts=None)
    assert r["status"] == p.LIVE_STATUS_CLOSED and r["closed"]["by"] == "cap"
    assert p.p2_window(p.ep("2026-11-10T00:00:00Z"))[0] == p.ep("2026-11-11T00:00:00Z")


def test_kalshi_book_parse():
    assert p.kalshi_book({"orderbook": {"yes_dollars": [["0.55", 10]], "no_dollars": [["0.40", 3]]}}) == {"k_bid": 0.55, "k_ask": pytest.approx(0.60)}
    assert p.kalshi_book({"orderbook": {"yes": [[55, 10]], "no": [[40, 3]]}})["k_bid"] == pytest.approx(0.55)
    assert math.isnan(p.kalshi_book({"orderbook": {}})["k_ask"])


def _live_fixture(live: Path, n: int, slope: float, gap: float = 0.08) -> dict:
    rng = np.random.default_rng(5)
    audits = {}
    for i in range(n):
        pid = f"K{i}|{i}"
        tb = NOW + i * 3 * HOUR
        m0 = float(rng.uniform(0.3, 0.6))
        g = float(rng.choice([-1, 1]) * gap * rng.uniform(0.8, 1.5))
        m1 = m0 + slope * g + float(rng.normal(0, 0.005))
        c15.jsonl_append(live / p.LIVE_FILES["pairs"], {"pair_id": pid, "eligible": True, "p_event_id": f"e{i // 2}", "matched_at": NOW, "fee_rate": 0.02})
        c15.jsonl_append(live / p.LIVE_FILES["first_prints"], {"pair_id": pid, "t_birth": tb, "late": False})
        for which, mid in (("t_d", m0), ("t_d+24h", m1)):
            k = m0 + g
            due = tb + 600 + (DAY if which == "t_d+24h" else 0.0)
            c15.jsonl_append(live / p.LIVE_FILES["books"], {"pair_id": pid, "which": which, "due": due, "receipt": due + 5.0, "yes": {"bid": mid - 0.005, "ask": mid + 0.005}, "no": {"bid": 1 - mid - 0.005, "ask": 1 - mid + 0.005},
                                                           "kalshi": {"k_bid": k - 0.01, "k_ask": k + 0.01}})
        audits[pid] = "pass"
    return audits


def test_rep_replicates_a_planted_effect_and_counts_power(tmp_path):
    live = tmp_path / "live"
    live.mkdir()
    audits = _live_fixture(live, 70, 0.7)
    res = p.rep_p(live, audits, ["P1", "P2"])
    assert res["P1"]["advance"] and res["P2"]["advance"], (res["P1"].get("checks"), res["P2"].get("checks"))
    assert res["stage2_holm"]["k"] == 2
    audits2 = dict(audits)
    for k in list(audits2)[:15]:
        audits2[k] = "fail"
    res2 = p.rep_p(live, audits2, ["P1"])
    assert res2["P1"]["verdict"] == p.NOT_RUN_POWER_REP and res2["labels"]["audit fail"] == 15
    with pytest.raises(c15.NotNow):
        p.read_audits(tmp_path / "none", {"2026-W46"})


# ---- freeze-check fixes (P-1 .. P-14) -------------------------------------------------------------------------------------------------------------------


def _born_pair(tmp_path, lim=None, cat="Politics"):
    """A pair matched, polled and born on a fake; returns (hist, live, lim, t_d)."""
    hist = tmp_path / "research_lab" / "history"
    q = "Will the Federal Reserve cut rates at the December 2026 meeting"
    lim = lim or LiveLim([_gm(1, NOW - 600, q)], [_km("FED-26DEC", q, NOW - 3 * DAY)], {"c1": [{"timestamp": NOW + 60, "price": 0.5, "size": 3, "outcomeIndex": 0, "transactionHash": "h"}]}, cat=cat)
    p.p_cache(hist, lim, now=NOW, freeze_ts=None, clock=lambda: NOW)
    p.p_live(hist, lim, lim, now=NOW + 30, rules_sha="x", freeze_ts=None, clock=lambda: NOW + 30)
    p.p_live(hist, lim, lim, now=NOW + 120, rules_sha="x", freeze_ts=None, clock=lambda: NOW + 120)
    return hist, hist / p.LIVE_RUN, lim, NOW + 60 + 600


def test_failed_read_is_retried_in_window_and_never_stored(tmp_path):
    hist, live, lim, td = _born_pair(tmp_path)
    lim.book_fail = 1
    r = p.p_live(hist, lim, lim, now=td + 5, rules_sha="x", freeze_ts=None, clock=lambda: td + 5)
    assert r["reads"] == 0 and r["read_failures"] == 1
    assert not (live / p.LIVE_FILES["books"]).exists()
    r = p.p_live(hist, lim, lim, now=td + 65, rules_sha="x", freeze_ts=None, clock=lambda: td + 65)  # retried inside the 2-min window
    assert r["reads"] == 1
    b = next(c15.jsonl_iter(live / p.LIVE_FILES["books"]))
    assert b["http_ok"] and b["receipt"] == td + 65 and b["due"] == td
    r = p.p_live(hist, lim, lim, now=td + 66, rules_sha="x", freeze_ts=None, clock=lambda: td + 66)
    assert r["reads"] == 0  # one read per pair and read


def test_read_after_the_window_is_missed_and_labelled_unavailable(tmp_path):
    hist, live, lim, td = _born_pair(tmp_path)
    lim.book_fail = 99
    p.p_live(hist, lim, lim, now=td + 10, rules_sha="x", freeze_ts=None, clock=lambda: td + 10)
    p.p_live(hist, lim, lim, now=td + 200, rules_sha="x", freeze_ts=None, clock=lambda: td + 200)  # past 2 min: missed
    lim.book_fail = 0
    p.p_live(hist, lim, lim, now=td + 260, rules_sha="x", freeze_ts=None, clock=lambda: td + 260)
    assert not (live / p.LIVE_FILES["books"]).exists()
    audits = {pid: "pass" for pid in (x["pair_id"] for x in c15.jsonl_iter(live / p.LIVE_FILES["pairs"]))}
    units, labels = p.rep_units(live, audits)
    assert not units and labels["unavailable (read)"] == 1 and "no two-sided quote at t_d" not in labels


def test_receipt_after_the_response_decides_not_invocation_start(tmp_path):
    hist, live, lim, td = _born_pair(tmp_path)
    ticks = iter([td + 119.0, td + 119.5, td + 125.0, td + 130.0, td + 131.0])  # the loop starts in the window, the response arrives after it
    p.p_live(hist, lim, lim, now=td + 119, rules_sha="x", freeze_ts=None, clock=lambda: next(ticks, td + 140))
    assert not (live / p.LIVE_FILES["books"]).exists()


def test_valid_reads_first_in_window_and_outside_discarded(tmp_path):
    live = tmp_path / "live"
    live.mkdir()
    tb = NOW
    c15.jsonl_append(live / p.LIVE_FILES["first_prints"], {"pair_id": "A", "t_birth": tb, "late": False})
    d0, d1 = tb + 600, tb + 600 + DAY
    for which, rc in (("t_d", d0 + 130.0), ("t_d", d0 + 10.0), ("t_d", d0 + 20.0), ("t_d+24h", d1 - 1.0), ("t_d+24h", d1 + 299.0)):
        c15.jsonl_append(live / p.LIVE_FILES["books"], {"pair_id": "A", "which": which, "receipt": rc, "marker": rc})
    r, labels = p.valid_reads(live)
    assert r["A"]["t_d"]["marker"] == d0 + 10.0 and r["A"]["t_d+24h"]["marker"] == d1 + 299.0
    assert labels["read outside its window (discarded)"] == 2 and labels["duplicate in-window read (first kept)"] == 1


def test_stop_rule_counts_only_usable_births(tmp_path):
    live = tmp_path / "live"
    live.mkdir()
    for i, (late, both) in enumerate([(False, True), (True, True), (False, False), (False, True)]):
        pid = f"P{i}"
        tb = NOW + i * 7 * HOUR
        c15.jsonl_append(live / p.LIVE_FILES["pairs"], {"pair_id": pid, "eligible": True, "matched_at": NOW})
        c15.jsonl_append(live / p.LIVE_FILES["first_prints"], {"pair_id": pid, "t_birth": tb, "late": late})
        c15.jsonl_append(live / p.LIVE_FILES["books"], {"pair_id": pid, "which": "t_d", "receipt": tb + 610})
        if both:
            c15.jsonl_append(live / p.LIVE_FILES["books"], {"pair_id": pid, "which": "t_d+24h", "receipt": tb + 610 + DAY + 3})
    c15.jsonl_append(live / p.LIVE_FILES["pairs"], {"pair_id": "X", "eligible": False, "matched_at": NOW})
    c15.jsonl_append(live / p.LIVE_FILES["first_prints"], {"pair_id": "X", "t_birth": NOW, "late": False})
    c15.jsonl_append(live / p.LIVE_FILES["books"], {"pair_id": "X", "which": "t_d", "receipt": NOW + 610})
    c15.jsonl_append(live / p.LIVE_FILES["books"], {"pair_id": "X", "which": "t_d+24h", "receipt": NOW + 610 + DAY})
    assert p.births_with_24h_read(live) == 2  # not late and both reads in their windows (an out-of-window 24-h receipt or an ineligible pair does not count)


def test_only_eligible_pairs_are_polled(tmp_path):
    hist, live, lim, _ = _born_pair(tmp_path, cat="Sports")
    assert not (live / p.LIVE_FILES["first_prints"]).exists()


def test_each_listing_is_logged_once_and_cap_blocks_new_pairs(tmp_path):
    hist = tmp_path / "research_lab" / "history"
    lim = LiveLim([_gm(1, NOW - 600, "Will something unrelated happen by the end of year")], [], {})
    p.p_cache(hist, lim, now=NOW, freeze_ts=None, clock=lambda: NOW)
    for k in range(3):
        p.p_live(hist, lim, lim, now=NOW + 3600 * (k + 1) * 0.9, rules_sha="x", freeze_ts=None, clock=lambda: NOW + 100)
        p.p_cache(hist, lim, now=NOW + 3600 * (k + 1) * 0.9, freeze_ts=None, clock=lambda: NOW + 100)
    assert len(list(c15.jsonl_iter(hist / p.LIVE_RUN / p.LIVE_FILES["listings"]))) == 1
    # the 0.05 GB live-dir cap: no new pair is taken, logged
    q = "Will the Federal Reserve cut rates at the December 2026 meeting"
    lim2 = LiveLim([_gm(2, NOW - 600, q)], [_km("FED-26DEC", q, NOW - 3 * DAY)], {})
    hist2 = tmp_path / "h2" / "research_lab" / "history"
    p.p_cache(hist2, lim2, now=NOW, freeze_ts=None, clock=lambda: NOW)
    (hist2 / p.LIVE_RUN / "pad.bin").write_bytes(b"x" * 64)  # live files over the cap (the cache folder is outside the live-file cap, inside the total)
    r = p.p_live(hist2, lim2, lim2, now=NOW + 30, rules_sha="x", freeze_ts=None, clock=lambda: NOW + 30, cap_bytes=10)
    assert r["matched"] == 0
    assert any("cap" in json.loads(x)["why"] for x in (hist2 / p.LIVE_RUN / p.LIVE_FILES["gaps"]).read_text().splitlines())


def test_cache_job_resumes_at_its_cursor_and_keeps_the_old_cache_until_complete(tmp_path):
    hist = tmp_path / "research_lab" / "history"
    q = "Will the Federal Reserve cut rates at the December 2026 meeting"
    lim = LiveLim([], [], {})
    lim.kalshi_pages = [[_km("A-1", q, NOW - 3 * DAY)], None, [_km("B-1", q + " again", NOW - 3 * DAY)]]
    r = p.p_cache(hist, lim, now=NOW, freeze_ts=None, clock=lambda: NOW)
    assert r["status"] == "p_cache_in_progress" and r["pages"] == 1
    assert not (hist / p.LIVE_RUN / p.CACHE_SUBDIR / p.CACHE_FILES["cache"]).exists()
    lim.kalshi_pages[1] = [_km("A-2", q + " two", NOW - 3 * DAY)]  # the page recovers
    r = p.p_cache(hist, lim, now=NOW + 60, freeze_ts=None, clock=lambda: NOW + 60)
    assert r["status"] == "p_cache_complete" and r["cached"] == 3 and r["pages"] == 2  # resumed at the cursor: pages 2 and 3 only
    assert p.p_cache(hist, lim, now=p.p2_window(None)[0] - 2 * DAY, freeze_ts=None)["status"] == "p_cache_idle"


def test_daily_cap_prioritises_reads_over_polls_and_scan(tmp_path):
    hist, live, lim, td = _born_pair(tmp_path)
    st = json.loads((live / p.LIVE_FILES["state"]).read_text())
    st["requests_day"] = p.DAILY_REQUEST_CAP - 5  # inside the read reserve: polls and scans stop, the read still runs
    (live / p.LIVE_FILES["state"]).write_text(json.dumps(st))
    r = p.p_live(hist, lim, lim, now=td + 5, rules_sha="x", freeze_ts=None, clock=lambda: td + 5)
    assert r["reads"] == 1


def test_sign_checks_top5_requires_p_and_the_floor():
    n = 40
    ev = [f"e{i}" for i in range(n)]
    wk = [f"w{i}" for i in range(n)]
    tb = [BASE + i * DAY for i in range(n)]
    pv = np.linspace(0.1, 1.0, n)
    est = lambda keep: 0.5  # noqa: E731
    ok = p.sign_checks(est, n, ev, wk, tb, pv, p_fn=lambda keep: {"testable": True, "p": 0.001, "small_g_rules_hold": True}, floor=0.3)
    assert ok["top5_event_drop"]["holds"] and ok["top5_week_drop"]["holds"]
    weak_p = p.sign_checks(est, n, ev, wk, tb, pv, p_fn=lambda keep: {"testable": True, "p": 0.2, "small_g_rules_hold": True}, floor=0.3)
    assert not weak_p["top5_event_drop"]["holds"]  # the sign survives but p >= 0.01
    low_floor = p.sign_checks(lambda keep: 0.1, n, ev, wk, tb, pv, p_fn=lambda keep: {"testable": True, "p": 0.001, "small_g_rules_hold": True}, floor=0.3)
    assert not low_floor["top5_week_drop"]["holds"]  # positive but below the floor


def _rep_fixture_with_wide_24h_books(live: Path, n: int, unavailable: int) -> dict:
    audits = _live_fixture(live, n, 0.7)
    rows = list(c15.jsonl_iter(live / p.LIVE_FILES["books"]))
    (live / p.LIVE_FILES["books"]).unlink()
    for b in rows:
        if b["which"] == "t_d+24h":
            if int(b["pair_id"].split("|")[0][1:]) < unavailable:
                continue  # no 24-h read at all
            b["yes"] = {"bid": float("nan"), "ask": 0.9}  # wide / one-sided book: the one-sided-bound rule still gives a mid
        c15.jsonl_append(live / p.LIVE_FILES["books"], b)
    return audits


def test_p1_rep_keeps_one_sided_24h_books_and_applies_the_availability_gate(tmp_path):
    live = tmp_path / "live"
    live.mkdir()
    audits = _rep_fixture_with_wide_24h_books(live, 70, 0)
    units, labels = p.rep_units(live, audits)
    assert len(units) == 70 and all(math.isfinite(u["delta"]) for u in units)
    assert p.mid_one_sided(math.nan, 0.9) == pytest.approx(0.45) and p.mid_one_sided(0.1, math.nan) == pytest.approx(0.55)
    live2 = tmp_path / "live2"
    live2.mkdir()
    audits2 = _rep_fixture_with_wide_24h_books(live2, 70, 35)  # 50% of the eligible have no 24-h read
    res = p.rep_p(live2, audits2, ["P1"])
    assert res["P1"]["verdict"] in (p.NOT_RUN_POWER_REP, p.NOT_TESTABLE_AVAIL)
    live3 = tmp_path / "live3"
    live3.mkdir()
    audits3 = _rep_fixture_with_wide_24h_books(live3, 100, 38)  # 62 available of 100 eligible would pass; 38% lost -> 62% >= 60%
    assert p.rep_p(live3, audits3, ["P1"])["P1"].get("availability", {}).get("ok")
    live4 = tmp_path / "live4"
    live4.mkdir()
    audits4 = _rep_fixture_with_wide_24h_books(live4, 150, 65)  # 85 of 150 = 57% < 60% with >= 60 units
    r4 = p.rep_p(live4, audits4, ["P1"])["P1"]
    assert r4["verdict"] == p.NOT_TESTABLE_AVAIL and not r4["advance"]


def test_rule_booleans_and_key_drop_labels():
    m = _meta(BASE + 3600, kt="K1", mid="1", ev="e1", cat="Politics", lead=48 * HOUR)
    tx = [{"ts": BASE + 3600, "vwap_yes": 0.5, "min_yes": 0.5, "max_yes": 0.5, "size": 10.0}]
    kc = np.array([[BASE + 3600 + t, 0.59, 0.61] for t in range(0, 1200, 60)])
    assert p.unit_features({**m, "k_bool_provisional": "False", "k_bool_close_early": "False"}, tx, kc)["label"] == "ok"
    assert p.unit_features({**m, "k_bool_provisional": "", "k_bool_close_early": ""}, tx, kc)["label"] == "ok"  # unknown is not an exclusion
    assert p.unit_features({**m, "k_bool_provisional": "True", "k_bool_close_early": "False"}, tx, kc)["label"] == "rule booleans differ (excluded)"
    assert p.unit_features({**m, "k_bool_close_early": "True"}, tx, kc)["label"] == "rule booleans differ (excluded)"
    assert p.unit_features({**m, "key_drop": "neg_risk_market:cb14"}, tx, kc)["label"].startswith("key drop")


def test_key_rule_rereads_absent_frames_and_checks_all_keys(tmp_path):
    hist = tmp_path / "history"
    (hist / "h14_wiki").mkdir(parents=True)
    import csv as _csv
    import gzip as _gz
    with _gz.open(hist / "h14_wiki" / "frame.csv.gz", "wt", newline="") as fh:
        w = _csv.writer(fh)
        w.writerow(["market_id", "neg_risk_market_id", "series_id", "other"])
        w.writerow(["900", "NR1", "S1", "x"])
    ksrc = {"market": {"900": {c15.C1_SOURCE}}, "event": {}, "neg_risk_market": {}, "series": {}}
    out, rep = p.reread_absent_frames(hist, ["h14_wiki/frame.csv.gz", "h11_pol/frame.csv.gz"], ksrc)
    assert rep["still_absent"] == ["h11_pol/frame.csv.gz"] and "h14_wiki/frame.csv.gz" in rep["reread"]
    assert c15.drop_reason({"market_id": "900"}, ksrc, "P") == ""  # C1-only before
    assert c15.drop_reason({"market_id": "900"}, out, "P").startswith("market:")
    assert c15.drop_reason({"market_id": "1", "neg_risk_market_id": "NR1"}, out, "P").startswith("neg_risk_market:")
    assert c15.drop_reason({"market_id": "1", "series_ids": "S1"}, out, "P").startswith("series:")
    assert ksrc["market"]["900"] == {c15.C1_SOURCE}  # the input is not mutated


def test_non_200_candles_leave_the_pair_pending(tmp_path):
    class Lim:
        requests = 0

        def __init__(self, candle_status):
            self.candle_status = candle_status

        def get(self, url, params):
            self.requests += 1
            if "trades" in url:
                return 200, [{"timestamp": BASE + 100, "price": 0.5, "size": 5, "outcomeIndex": 0, "transactionHash": "h"}]
            if "candlesticks" in url:
                return self.candle_status, ({"candlesticks": []} if self.candle_status == 200 else None)
            if "prices-history" in url:
                return 200, {"history": []}
            raise AssertionError(url)

    (tmp_path / "creative_batch15").mkdir()
    frame = tmp_path / "creative_batch15" / "birth_frame.csv.gz"
    p.write_birth_frame(frame, [["K1", "S", "Politics", "/live", "1", "e1", p.cm.iso(BASE - 3 * DAY), p.cm.iso(BASE), 72.0, 0.0, 1.0]])
    hist = tmp_path / "research_lab" / "history"
    gm = {"1": {"id": "1", "conditionId": "c1", "outcomes": '["Yes","No"]', "clobTokenIds": '["a","b"]', "events": [{"id": "e1", "series": [{"id": "S9"}]}], "negRiskMarketID": "NR9"}}
    lim = Lim(200)
    kl = Lim(500)
    r = p.p_data(hist, lim, kl, frame_path=frame, gamma_lookup=lambda ids: gm)
    assert r["status"] == p.P_DATA_PROGRESS and r["pending_read_failures"] == ["K1"]
    d = hist / p.DATA_RUN
    assert not (d / p.DATA_FILES["work"]).exists() or "K1" not in (d / p.DATA_FILES["work"]).read_text()
    att = list(c15.jsonl_iter(d / p.DATA_FILES["attempts"]))
    assert att and any("kalshi_candles:500" in k for k in att[0]["statuses"])
    kl.candle_status = 200  # the retry completes and records the request statuses and the new keys
    r = p.p_data(hist, lim, kl, frame_path=frame, gamma_lookup=lambda ids: gm, ksrc={"market": {}, "event": {}, "neg_risk_market": {"NR9": {"cb14"}}, "series": {}})
    assert r["status"] == p.P_DATA_STATUS
    rec = next(c15.jsonl_iter(d / p.DATA_FILES["work"]))
    assert rec["key_drop"].startswith("neg_risk_market:") and rec["req"]


def test_census_reports_target_availability_counts():
    data, _ = _synth(80)
    c = p.census_p(data)
    t = c["targets"]
    assert set(t) == {"print_target", "history_target", "no_target"} and t["print_target"] + t["history_target"] + t["no_target"] == c["labels"]["ok"]
    assert "rule_booleans" in c and "key_drops" in c


# ---- re-check fixes (P-16 .. P-22) --------------------------------------------------------------------------------------------------------------------


def test_scheduled_end_before_the_24h_read_excludes_the_pair_before_any_read(tmp_path):
    """P-16: endDate < t_d + 25 h -> 'ends early (scheduled)': no reads (so no 404 is ever read as an empty book), counted, outside the availability denominators."""
    hist = tmp_path / "research_lab" / "history"
    q = "Will the Federal Reserve cut rates at the December 2026 meeting"
    gm = _gm(1, NOW - 600, q)
    gm["endDate"] = p.cm.iso(NOW + 5 * HOUR)
    km = _km("FED-26DEC", q, NOW - 3 * DAY)
    km["close_time"] = gm["endDate"]
    lim = LiveLim([gm], [km], {"c1": [{"timestamp": NOW + 60, "price": 0.5, "size": 3, "outcomeIndex": 0, "transactionHash": "h"}]})
    p.p_cache(hist, lim, now=NOW, freeze_ts=None, clock=lambda: NOW)
    p.p_live(hist, lim, lim, now=NOW + 30, rules_sha="x", freeze_ts=None, clock=lambda: NOW + 30)
    p.p_live(hist, lim, lim, now=NOW + 120, rules_sha="x", freeze_ts=None, clock=lambda: NOW + 120)
    live = hist / p.LIVE_RUN
    b = next(c15.jsonl_iter(live / p.LIVE_FILES["first_prints"]))
    assert b["ends_early"] is True
    td = NOW + 60 + 600
    r = p.p_live(hist, lim, lim, now=td + 5, rules_sha="x", freeze_ts=None, clock=lambda: td + 5)
    assert r["reads"] == 0 and not (live / p.LIVE_FILES["books"]).exists()
    assert p.births_with_24h_read(live) == 0
    units, labels = p.rep_units(live, {pid: "pass" for pid in (x["pair_id"] for x in c15.jsonl_iter(live / p.LIVE_FILES["pairs"]))})
    assert not units and labels["ends early (scheduled)"] == 1 and "eligible for availability" not in labels


def test_a_404_at_the_24h_read_is_unavailable_not_an_empty_book(tmp_path):
    live = tmp_path / "live"
    live.mkdir()
    audits = _live_fixture(live, 70, 0.7)
    rows = list(c15.jsonl_iter(live / p.LIVE_FILES["books"]))
    (live / p.LIVE_FILES["books"]).unlink()
    for b in rows:
        if b["which"] == "t_d+24h" and int(b["pair_id"].split("|")[0][1:]) < 5:
            b["yes"] = {"bid": float("nan"), "ask": float("nan")}
            b["statuses"] = {"yes": 404, "kalshi": "not requested", "no": "not requested"}
        c15.jsonl_append(live / p.LIVE_FILES["books"], b)
    units, labels = p.rep_units(live, audits)
    assert labels[p.NO_BOOK_24H] == 5 and labels["ok"] == 65
    bad = [u for u in units if u.get("unavailable_24h")]
    assert len(bad) == 5 and all(math.isnan(u["delta"]) for u in bad) and p.rep_p2_net(bad[0]) is None  # in the denominators, in no estimate


def test_24h_read_does_not_request_kalshi_and_only_the_needed_legs():
    """P-18: a failed (unused) Kalshi leg at 24 h cannot drop the unit, because Kalshi is not read at 24 h."""
    lim = LiveLim([], [], {})
    pair = {"token_yes": "y", "token_no": "n", "k_ticker": "K"}
    td = p.read_books(lim, lim, pair, "t_d")
    assert td["http_ok"] and td["statuses"]["kalshi"] == 200
    n0 = lim.requests
    z = p.read_books(lim, lim, pair, "t_d+24h", td)
    assert z["http_ok"] and z["statuses"]["kalshi"] == "not requested" and lim.requests - n0 <= 2
    assert p.READ_MAX_REQUESTS == 3


def test_a_read_never_overshoots_the_daily_cap(tmp_path):
    hist, live, lim, td = _born_pair(tmp_path)
    st = json.loads((live / p.LIVE_FILES["state"]).read_text())
    st["requests_day"] = p.DAILY_REQUEST_CAP - 2  # a read can need 3 requests: no room, deferred
    (live / p.LIVE_FILES["state"]).write_text(json.dumps(st))
    r = p.p_live(hist, lim, lim, now=td + 5, rules_sha="x", freeze_ts=None, clock=lambda: td + 5)
    assert r["reads"] == 0
    assert json.loads((live / p.LIVE_FILES["state"]).read_text())["requests_day"] <= p.DAILY_REQUEST_CAP


def test_pair_that_always_fails_becomes_unavailable_source_and_the_run_completes(tmp_path):
    """P-17: >= 3 failed attempts in 3 separate runs spanning >= 15 min -> 'unavailable (source)' (finished, counted, never a unit)."""

    class Lim:
        requests = 0

        def get(self, url, params):
            self.requests += 1
            if "trades" in url:
                return 200, [{"timestamp": BASE + 100, "price": 0.5, "size": 5, "outcomeIndex": 0, "transactionHash": "h"}]
            if "candlesticks" in url:
                return 500, None
            if "prices-history" in url:
                return 200, {"history": []}
            raise AssertionError(url)

    (tmp_path / "creative_batch15").mkdir()
    frame = tmp_path / "creative_batch15" / "birth_frame.csv.gz"
    p.write_birth_frame(frame, [["K1", "S", "Politics", "/live", "1", "e1", p.cm.iso(BASE - 3 * DAY), p.cm.iso(BASE), 72.0, 0.0, 1.0]])
    hist = tmp_path / "research_lab" / "history"
    gm = {"1": {"id": "1", "conditionId": "c1", "outcomes": '["Yes","No"]', "clobTokenIds": '["a","b"]', "events": [{"id": "e1"}]}}
    for t in (1000.0, 1500.0):  # two failed runs: still pending
        r = p.p_data(hist, Lim(), Lim(), frame_path=frame, gamma_lookup=lambda ids: gm, clock=lambda t=t: t)
        assert r["status"] == p.P_DATA_PROGRESS
    r = p.p_data(hist, Lim(), Lim(), frame_path=frame, gamma_lookup=lambda ids: gm, clock=lambda: 2000.0)  # third failed attempt, span 1000 s >= 900 s
    assert r["status"] == p.P_DATA_PROGRESS
    r = p.p_data(hist, Lim(), Lim(), frame_path=frame, gamma_lookup=lambda ids: gm, clock=lambda: 2100.0)
    assert r["status"] == p.P_DATA_STATUS and r["complete"]
    d = hist / p.DATA_RUN
    rec = next(c15.jsonl_iter(d / p.DATA_FILES["work"]))
    assert rec["status"] == p.UNAVAILABLE_SOURCE and rec["attempts"] == 3
    assert p.unit_features(rec, [], np.zeros((0, 5)))["label"] == p.UNAVAILABLE_SOURCE


def test_too_few_attempts_or_too_short_a_span_does_not_terminate(tmp_path):
    class Lim:
        requests = 0

        def get(self, url, params):
            self.requests += 1
            if "trades" in url:
                return 200, [{"timestamp": BASE + 100, "price": 0.5, "size": 5, "outcomeIndex": 0, "transactionHash": "h"}]
            return (500, None) if "candlesticks" in url else (200, {"history": []})

    (tmp_path / "creative_batch15").mkdir()
    frame = tmp_path / "creative_batch15" / "birth_frame.csv.gz"
    p.write_birth_frame(frame, [["K1", "S", "Politics", "/live", "1", "e1", p.cm.iso(BASE - 3 * DAY), p.cm.iso(BASE), 72.0, 0.0, 1.0]])
    hist = tmp_path / "research_lab" / "history"
    gm = {"1": {"id": "1", "conditionId": "c1", "outcomes": '["Yes","No"]', "clobTokenIds": '["a","b"]', "events": [{"id": "e1"}]}}
    for t in (1000.0, 1100.0, 1200.0, 1300.0, 1400.0):  # 5 runs but only 400 s apart (< 15 min)
        r = p.p_data(hist, Lim(), Lim(), frame_path=frame, gamma_lookup=lambda ids: gm, clock=lambda t=t: t)
        assert r["status"] == p.P_DATA_PROGRESS


def test_kalshi_cache_folder_is_capped_and_counted_in_the_live_total(tmp_path, monkeypatch):
    hist = tmp_path / "research_lab" / "history"
    q = "Will the Federal Reserve cut rates at the December 2026 meeting"
    lim = LiveLim([_gm(2, NOW - 600, q)], [_km("FED-26DEC", q, NOW - 3 * DAY)], {})
    p.p_cache(hist, lim, now=NOW, freeze_ts=None, clock=lambda: NOW)
    cdir = hist / p.LIVE_RUN / p.CACHE_SUBDIR
    assert (cdir / p.CACHE_FILES["cache"]).is_file() and p._dir_bytes(hist / p.LIVE_RUN) > p._dir_bytes(hist / p.LIVE_RUN, exclude=cdir)
    # the cache job stops paging over its own cap (the old cache stays)
    monkeypatch.setattr(p, "CACHE_DIR_CAP_BYTES", 10)
    lim.kalshi_pages = [[_km("A-1", q, NOW - 3 * DAY)], [_km("B-1", q + " b", NOW - 3 * DAY)]]
    r = p.p_cache(hist, lim, now=NOW + 5 * HOUR, freeze_ts=None, clock=lambda: NOW + 5 * HOUR)
    assert r["pages"] == 0 and any("cap" in json.loads(x)["why"] for x in (cdir / p.CACHE_FILES["gaps"]).read_text().splitlines())
    # the watcher counts the cache in the total: live cap + cache cap
    (hist / p.LIVE_RUN / "pad.bin").write_bytes(b"x" * 1000)
    r = p.p_live(hist, lim, lim, now=NOW + 5 * HOUR + 30, rules_sha="x", freeze_ts=None, clock=lambda: NOW + 5 * HOUR + 30, cap_bytes=500)
    assert r["matched"] == 0


def test_combined_kalshi_rate_is_at_most_one_per_second():
    import importlib.util
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    run = importlib.import_module("run_cb15")
    assert run.DECLARED_KALSHI_RPS_BY_CMD["p-live"] + run.DECLARED_KALSHI_RPS_BY_CMD["p-cache"] <= 1.0
    assert importlib.util.find_spec("run_cb15") is not None


def test_poly_rule_booleans_declared_unknown_and_kalshi_true_flag_excludes():
    assert p.POLY_RULE_BOOLEANS == "unknown"
    assert p.rule_booleans_differ({"k_bool_provisional": True}) and not p.rule_booleans_differ({"k_bool_provisional": False}) and not p.rule_booleans_differ({})
