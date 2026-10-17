# ruff: noqa: E501
"""CB9-P tests (offline; constructed Yahoo replies, books and prints)."""

from __future__ import annotations

import json
import math

import numpy as np
import pytest

from astrolabe.research_lab import cb9_common as c9
from astrolabe.research_lab import cb9_pyth as py

DAY = "2026-09-15"  # out-of-window full session (EDT)


def chart(rows: list[tuple[float, float, float]]) -> dict:
    """Yahoo v8 reply from (start epoch, open, close)."""
    return {"chart": {"result": [{"timestamp": [int(r[0]) for r in rows], "indicators": {"quote": [{
        "open": [r[1] for r in rows], "high": [max(r[1], r[2]) for r in rows], "low": [min(r[1], r[2]) for r in rows], "close": [r[2] for r in rows]}]}}]}}


def hourly_rows(day: str, closes: list[float] | None = None, *, closing_row: bool = True, pre_open: bool = True, half: bool = False) -> list[tuple]:
    starts = [(9, 30), (10, 30), (11, 30), (12, 30)] + ([] if half else [(13, 30), (14, 30), (15, 30)])
    closes = closes or [100.0 + i for i in range(len(starts))]
    rows = [(py.et_epoch(day, h, m), c - 0.5, c) for (h, m), c in zip(starts, closes, strict=True)]
    if pre_open:
        rows.insert(0, (py.et_epoch(day, 8, 30), 99.0, 99.2))
    if closing_row:
        ch = 13 if half else 16
        rows.append((py.et_epoch(day, ch, 0), closes[-1], closes[-1]))
    return rows


# ---- bar clock -------------------------------------------------------------------------------------------------------------------


def test_bar_parser_eighth_closing_row_dropped():
    rows = py.parse_chart(chart(hourly_rows(DAY)))
    assert len([r for r in rows if py.et_day(r["o"]) == DAY]) == 9  # 7 bars + closing row + pre-open row
    bars, info = py.session_bars(rows, DAY)
    assert bars is not None and len(bars) == 7 and info["status"] == "ok"
    assert info["dropped_at_or_after_close"] == 1 and info["dropped_pre_open"] == 1 and info["first_start_0930"]
    assert bars[0]["o"] == py.et_epoch(DAY, 9, 30) and bars[0]["e"] == py.et_epoch(DAY, 10, 30)
    assert bars[-1]["o"] == py.et_epoch(DAY, 15, 30) and bars[-1]["e"] == py.et_epoch(DAY, 16, 0)  # 30-minute last bar


def test_bar_parser_wrong_count_unavailable_and_missing_close():
    rows = py.parse_chart(chart(hourly_rows(DAY)[:-3]))
    bars, info = py.session_bars(rows, DAY)
    assert bars is None and info["status"] == "bars_unavailable"
    doc = chart(hourly_rows(DAY))
    doc["chart"]["result"][0]["indicators"]["quote"][0]["close"][3] = None
    assert py.session_bars(py.parse_chart(doc), DAY)[0] is None


def test_half_session_13_et():
    day = "2026-11-27"
    bars, info = py.session_bars(py.parse_chart(chart(hourly_rows(day, half=True))), day)
    assert bars is not None and len(bars) == py.HALF_BARS
    assert bars[-1]["e"] == py.et_epoch(day, 13, 0) and info["dropped_at_or_after_close"] == 1


def test_usable_at_checkpoints():
    bars, _ = py.session_bars(py.parse_chart(chart(hourly_rows(DAY))), DAY)
    ck = py.checkpoints(DAY)
    assert [round(t - e) for _, e, t in ck] == [120, 120, 120]
    got = [py.latest_usable(bars, t)["o"] for _, _, t in ck]
    assert got == [py.et_epoch(DAY, 9, 30), py.et_epoch(DAY, 11, 30), py.et_epoch(DAY, 14, 30)]
    assert py.latest_usable(bars, py.et_epoch(DAY, 10, 31) + 59) is None  # 10:31:59: the 09:30 bar is not yet usable
    assert py.datetime.fromtimestamp(ck[0][2], py.ET).strftime("%H:%M") == "10:32"


def test_smoke_yahoo_check_pass_and_fail():
    rows = hourly_rows(SMOKE := py.SMOKE_SESSIONS[0]) + hourly_rows(py.SMOKE_SESSIONS[1])
    daily = chart([(py.et_epoch(d, 9, 30), 99.5, 106.0) for d in py.SMOKE_SESSIONS])
    res = py.smoke_yahoo_check(chart(rows), daily)
    assert res["pass"] and res["sessions"][SMOKE]["dropped_at_or_after_close"] == 1
    bad = chart([(py.et_epoch(d, 9, 30), 101.0, 106.0) for d in py.SMOKE_SESSIONS])  # open off by > 0.2%
    assert not py.smoke_yahoo_check(chart(rows), bad)["pass"]


# ---- model ---------------------------------------------------------------------------------------------------------------------


def test_sigma_needs_100_returns():
    sessions = py.full_sessions("2026-03-01", "2026-05-01")
    bars = {d: [{"o": 0, "e": 0, "open": 100.0, "close": 100.0 * math.exp(0.01 * ((i + j) % 3 - 1))} for j in range(6)] for i, d in enumerate(sessions)}
    day = sessions[-1]
    s = py.sigma_for(day, bars, sessions)
    assert s is not None and s > 0
    few = {d: v for d, v in bars.items() if d >= sessions[-17]}
    assert py.sigma_for(day, few, sessions) is None  # 16 sessions x 6 = 96 returns


def test_fair_value_and_fee():
    assert py.fair_up(100, 100, 0.01, 3.0) == pytest.approx(0.5)
    assert py.fair_up(101, 100, 0.01, 3.0) > py.fair_up(100.5, 100, 0.01, 3.0) > 0.5
    assert py.fair_up(100, 100, None, 3.0) is None
    assert py.fee_rate(None) == 0.04 and py.fee_rate(1000) == 0.10 and py.fee_rate(100) == 0.04
    assert py.tau_hours(DAY, py.checkpoints(DAY)[0][2]) == pytest.approx(5.4667, abs=1e-3)


def _book(ask, size=50.0, fresh=True, crossed=False, fee=None):
    return {"best_ask": ask, "ask_size": size, "fresh": fresh, "crossed": crossed, "fee_bps": fee}


def test_p1_unit_edge_size_fresh():
    t = py.p1_unit(0.80, {"up": _book(0.70), "down": _book(0.32)})
    assert t["token"] == "up" and t["edge"] == pytest.approx(0.80 - 0.70 - 0.04 * 0.7 * 0.3)
    assert py.p1_unit(0.75, {"up": _book(0.70)}) is None  # edge 0.0416 < 5c
    assert py.p1_unit(0.80, {"up": _book(0.70, size=4.0)}) is None
    assert py.p1_unit(0.80, {"up": _book(0.70, fresh=False)}) is None
    assert py.p1_unit(0.80, {"up": _book(0.70, crossed=True)}) is None
    d = py.p1_unit(0.20, {"up": _book(0.25), "down": _book(0.70)})
    assert d["token"] == "down"
    assert py.p1_net(t, 1.0) == pytest.approx(1.0 - 0.70 - t["fee"])


def test_p2_quotes_passive_cap():
    q = py.p2_quotes(0.555, 0.50, 0.52, 0.01)
    assert q["model"] == (0.51, 0.57)  # bid capped at best ask - tick
    assert q["mid"] == (0.50, 0.52)
    q = py.p2_quotes(0.40, 0.50, 0.52, 0.01)
    assert q["model"][1] >= 0.51  # ask >= best bid + tick


def test_quote_fills_queue_and_through_and_pnl():
    t = 1000.0
    rows = [{"ts": 1010, "idx": 1, "side": "BUY", "price": 0.52, "size": 30.0},  # taker BUY Down at 0.52 = sells Up at 0.48
            {"ts": 1020, "idx": 0, "side": "BUY", "price": 0.60, "size": 25.0}]
    pr = py.up_prints(rows, up_idx=0)
    r = py.quote_pair_pnl(pr, t, 0.48, 0.58, 0.0, 0.0, 1.0)
    assert r["bid_filled"] and r["ask_filled"] and r["pnl"] == pytest.approx(20 * (1 - 0.48) + 20 * (0.58 - 1.0))
    r2 = py.quote_pair_pnl(pr, t, 0.48, 0.58, 0.0, 0.0, 1.0, rule="through")
    assert not r2["bid_filled"] and r2["ask_filled"]  # bid only touched, not traded through
    r3 = py.quote_pair_pnl(pr, t, 0.48, 0.58, 15.0, 0.0, None)
    assert not r3["bid_filled"] and "pnl" not in r3  # 15 ahead + 20 own > 30 traded


def test_outcome_y():
    assert py.outcome_y(["Up", "Down"], ["0.5", "0.5"], "up") == 0.5
    assert py.outcome_y(["Down", "Up"], ["0", "1"], "up") == 1.0
    assert py.outcome_y(["Up", "Down"], ["0.97", "0.03"], "up") is None


# ---- frame parsing -----------------------------------------------------------------------------------------------------------


DESC = ('This market will resolve to "Up" if the Pyth "Close" value of the 1-minute candle for the final minute of regular trading on the most recent '
        'prior trading day ... If the two prices are exactly equal, this market will resolve 50-50. If NVIDIA does not trade during the regular session, '
        'the market will resolve 50-50.')


def _mkt(**kw) -> dict:
    m = {"id": 9, "conditionId": "0xc", "question": "NVIDIA (NVDA) Up or Down on September 15?", "resolutionSource": "https://pythdata.app/explore/Equity.US.NVDA%2FUSD",
         "description": DESC, "outcomes": '["Up", "Down"]', "clobTokenIds": '["t_up", "t_down"]', "negRisk": False, "events": [{"id": 5}]}
    m.update(kw)
    return m


def test_parse_market_primary_and_exclusions():
    r, why = py.parse_market(_mkt(), DAY)
    assert why == "ok" and r["ticker"] == "NVDA" and r["token_up"] == "t_up" and r["up_idx"] == 0
    assert py.parse_market(_mkt(outcomes='["Down", "Up"]'), DAY)[0]["token_up"] == "t_down"
    assert py.parse_market(_mkt(resolutionSource="https://pythdata.app/explore/Equity.US.TSLA/USD"), DAY)[1] == "source_re"
    assert py.parse_market(_mkt(question="NVIDIA (NVDA) Opens Up or Down on September 15?"), DAY)[1] == "opens_market"
    assert py.parse_market(_mkt(question="Will NVIDIA (NVDA) close above $180 on September 15?"), DAY)[1] == "strike_market"
    assert py.parse_market(_mkt(negRisk=True), DAY)[1] == "neg_risk"
    assert py.parse_market(_mkt(description=DESC.replace("50-50", "Down")), DAY)[1].startswith("flags:")


def test_calendar_and_windows():
    days = py.p_days()
    assert "2026-06-15" not in days and "2026-05-25" not in days and "2026-07-03" not in days and "2026-06-19" not in days
    assert days[0] == "2026-04-13" and days[-1] < "2026-08-10"
    assert py.gamma_end_window("2026-06-22") == ("2026-06-22T19:59:00Z", "2026-06-22T20:01:00Z")
    assert py.gamma_end_window("2026-11-16") == ("2026-11-16T20:59:00Z", "2026-11-16T21:01:00Z")
    assert py.datetime.fromtimestamp(py.checkpoints("2026-11-16")[0][2], py.UTC).strftime("%H:%M") == "15:32"  # EST: +1 h in UTC


# ---- guards ----------------------------------------------------------------------------------------------------------------------


def test_guarded_files_only_in_screen_jobs(tmp_path):
    from astrolabe.research_lab import history_backfill as hb

    p = tmp_path / "outcomes_guarded.csv.gz"
    p.write_bytes(hb._gz_csv_bytes(py.OUTCOME_COLUMNS, [["1", DAY, '["Up","Down"]', '["1","0"]']]))
    for job in ("census", "pyth-frame", "pyth-books", "smoke"):
        with pytest.raises(c9.Refused):
            py.open_guarded(p, job)
    assert py.open_guarded(p, "screen-P")[0]["market_id"] == "1"
    other = tmp_path / "bars_pre.csv.gz"
    other.write_bytes(p.read_bytes())
    with pytest.raises(c9.Refused):
        py.open_guarded(other, "screen-P")


def test_census_p_refuses_targets_and_labels():
    u = {"label": "ok", "day": DAY, "ticker": "NVDA", "trade": None, "p2": None, "n_prints_window": 1, "pmxt_events_window": 0}
    with pytest.raises(c9.Refused):
        py.census_p([{**u, "net": 0.1}], {})
    res = py.census_p([u], {})
    assert res["coverage_audit"]["pass"] is False and res["label_P1"] == "not testable (source unavailable)"
    ok = [{**u, "pmxt_events_window": 3} for _ in range(10)]
    res = py.census_p(ok, {})
    assert res["coverage_audit"]["pass"] and res["label_P1"].startswith("no opportunity")


# ---- Stage 2 ------------------------------------------------------------------------------------------------------------------


def test_live_s_t_uses_receipt_time_and_no_substitute():
    doc = chart(hourly_rows("2026-11-16"))
    e = py.et_epoch("2026-11-16", 10, 30)
    assert py.live_s_t(doc, "2026-11-16", e + 119) is None
    assert py.live_s_t(doc, "2026-11-16", e + 120) == 100.0
    assert py.checkpoint_status(True, None, True).startswith("unavailable (source)")
    assert py.checkpoint_status(True, 1.0, False).startswith("unavailable (source)")
    assert py.checkpoint_status(True, 1.0, True) == "ok"


def test_stage2_partial_failure_rule():
    sess = py.stage2_sessions("2026-11-16")
    assert len(sess) == 30 and "2026-11-26" not in sess and "2026-11-27" not in sess and "2026-12-25" not in sess and "2026-12-24" not in sess
    status = {(s, i): "ok" for s in sess for i in range(3)}
    assert py.stage2_availability(status, sess)["testable"]
    for s in sess[:6]:  # 6 whole sessions lost (sigma/K_d failed): 18 of 90 = 20% -> still testable
        for i in range(3):
            status[(s, i)] = "unavailable (source): sigma/K_d fetch failed"
    r = py.stage2_availability(status, sess)
    assert r["sessions"] == 30 and r["share"] == pytest.approx(0.2) and r["testable"]
    status[(sess[7], 0)] = "unavailable (source)"
    assert py.stage2_availability(status, sess)["label"] == "not testable (source unavailable)"


def test_t9_p2_start_skips_non_sessions():
    assert py.t9_p2_start(py.datetime(2026, 11, 25, 12, tzinfo=py.UTC).timestamp()) == "2026-11-30"  # +1 d = Thanksgiving; 27th is a half session
    assert py.t9_p2_start(py.datetime(2026, 11, 2, 12, tzinfo=py.UTC).timestamp()) == "2026-11-03"


def test_build_units_features_only_and_stale(tmp_path):
    day = "2026-05-15"
    sessions = py.full_sessions(py.BARS_FROM, "2026-05-16")[-21:]  # 20 prior sessions + the day itself
    bars = {}
    rng = np.random.default_rng(3)
    for s in sessions:
        c = 100.0 * np.exp(np.cumsum(rng.normal(0, 0.005, 6)))
        bars[("NVDA", s)] = [{"o": py.et_epoch(s, 9, 30) + 3600 * j, "e": py.et_epoch(s, 9, 30) + 3600 * (j + 1), "open": 100.0, "close": float(c[j])}
                             for j in range(6)]
    frame = [{"market_id": "1", "ticker": "NVDA", "day": day, "up_idx": "0", "token_up": "a", "token_down": "b", "condition_id": "c"}]
    states = []
    for ci in range(3):
        for tok, ask in (("up", 0.30), ("down", 0.75)):
            states.append({"market_id": "1", "day": day, "ckpt": ci, "lag_s": 120, "token": tok, "fresh": "1", "crossed": "0", "best_bid": str(ask - 0.02),
                           "best_ask": str(ask), "ask_size": "100", "fee_bps": "", "tick": "0.01", "n_events_window": "2",
                           "bids_top": json.dumps([[ask - 0.02, 10.0]]), "asks_top": json.dumps([[ask, 100.0]])})
    units = py.build_units(frame, bars, {("NVDA", day): float(bars[("NVDA", sessions[-2])][-1]["close"])}, states, [])
    assert len(units) == 3 and all(u["label"] == "ok" and u["sigma"] for u in units)
    assert all("y" not in u and "net" not in u for u in units)
    stale = py.build_units(frame, bars, {("NVDA", day): 100.0}, states, [], stale=True)
    assert stale[0]["s_t"] == bars[("NVDA", sessions[-2])][-1]["close"]  # 10:32 stale anchor = prior session's 14:30 bar


def test_rules_doc_pyth_roundtrip(tmp_path):
    p = c9.write_rules("pyth", tmp_path / "r.json")
    sha, fp = c9.verify_rules("pyth", p, require_committed=False)
    assert fp == "" and len(sha) == 64
    d = json.loads(p.read_text())["declared"]
    assert d["clock"]["full_bars"] == 7 and d["p1"]["edge"] == 0.05 and d["stage2"]["unavailable_max"] == 0.20


# ---- freeze-check fixes (M3, M4, M5, M9, M10) --------------------------------------------------------------------------------------

CURRENT = ('This market will resolve to "Up" if the Pyth "Close" value of the 1-minute candle corresponding to the final minute of regular trading hours for '
           'NVIDIA (NVDA) is higher than the close of the most recent prior trading day. If the two specified closing prices are exactly equal, this market '
           'will resolve 50-50. Closing prices will be used exactly as published by Pyth, without rounding. If NVIDIA (NVDA) does not trade at all during the '
           'regular session, the market will resolve 50-50.')


def test_flags_current_text_and_same_sentence_equality():
    assert py.parse_market(_mkt(description=CURRENT), DAY)[1] == "ok"
    down = CURRENT.replace("If the two specified closing prices are exactly equal, this market will resolve 50-50.",
                           'If the two specified closing prices are exactly equal, this market will resolve to "Down".')
    r, why = py.parse_market(_mkt(description=down), DAY)
    assert r is None and why == "flags:equality_50_50"  # the following no-trade 50-50 sentence must not satisfy the equality flag


def test_old_2025_versions_excluded():
    old = CURRENT.replace("Closing prices will be used exactly as published by Pyth, without rounding.", "Prices are rounded to the nearest cent.")
    assert py.parse_market(_mkt(description=old), DAY)[1] == "old_version_rounded"
    vs_open = CURRENT + " The official closing price is compared with the official opening price."
    assert py.parse_market(_mkt(description=vs_open), DAY)[1] == "old_version_vs_open"


def test_smoke_gamma_paging_records_reasons_and_excerpt():
    class Lim:
        def get(self, url, params):
            if params.get("offset", 0):
                return 200, []
            return 200, [_mkt(description=CURRENT), _mkt(id=10, question="Will NVIDIA (NVDA) close above $180 on September 15?")]

    res = py.smoke_gamma_paging(Lim(), days=(DAY,))
    d = res["days"][DAY]
    assert res["pass"] and d["parse_reasons_first"] == {"ok": 1, "strike_market": 1}
    assert d["equality_excerpts_primary"] == ["If the two specified closing prices are exactly equal, this market will resolve 50-50."]


def test_pyth_frame_and_books_stall(tmp_path):
    smoke = tmp_path / "smoke.json"
    smoke.write_text(json.dumps({"smoke_version": "cb9-smoke-v2", "criteria": {"yahoo_clock": False, "gamma_paging": True, "pmxt_heads": True}}))
    m = py.pyth_frame(tmp_path / "cb9", None, rules_sha="x", smoke_path=smoke, exclusion_keys_path=tmp_path / "k.csv.gz", now=c9.T_SEAL_EPOCH + 1)
    assert m["status"] == c9.STALL_NOT_RUN_SOURCE and m["label"] == "not testable (source)"
    b = py.pyth_books(tmp_path / "cb9", None, rules_sha="x", smoke_path=smoke, frame_dir=tmp_path / "cb9" / "pyth_frame", fetch=None, size_fn=None, now=c9.T_SEAL_EPOCH + 1)
    assert b["status"] == c9.STALL_UPSTREAM and b["label"] == "not testable (source)"


def test_fetch_outcomes_guarded_and_final(tmp_path):
    day = "2026-11-16"
    mk = [{"market_id": "1"}, {"market_id": "2"}]
    rows = [{"id": "1", "closed": True, "outcomes": '["Up","Down"]', "outcomePrices": '["1","0"]'},
            {"id": "2", "closed": True, "outcomes": '["Up","Down"]', "outcomePrices": '["0.6","0.4"]'}]  # not resolved yet
    st = py.fetch_outcomes(tmp_path, day, py.et_epoch(day, 23, 0), mk, lambda ids: rows)
    assert st["n_resolved"] == 1 and st["n_unresolved"] == 1 and not st["final"]
    assert py.open_guarded(tmp_path / "outcomes_guarded.csv.gz", "rep-P")[0]["market_id"] == "1"
    st = py.fetch_outcomes(tmp_path, day, py.et_epoch(day, 16, 0) + 8 * 86400, mk, lambda ids: [])
    assert st["final"] and st["n_unresolved"] == 1  # unresolved after 7 days: recorded, never guessed


def test_live_tick_fetches_outcomes_for_past_sessions(tmp_path):
    sess = py.stage2_sessions("2026-11-16")
    (tmp_path / sess[0]).mkdir()
    (tmp_path / sess[0] / "state.json").write_text(json.dumps({"steps": {"post": {"t": 1}}}))
    calls = []
    res = py.pyth_live_tick(tmp_path, now=py.et_epoch(sess[1], 8, 0), start_day=sess[0], frame_markets=lambda d: [{"market_id": "1", "ticker": "NVDA"}],
                            yahoo_get=None, book_get=None, prints_get=None, sessions=sess,
                            outcome_get=lambda ids: calls.append(ids) or [{"id": "1", "closed": True, "outcomes": '["Up","Down"]', "outcomePrices": '["0","1"]'}])
    assert f"outcomes:{sess[0]}" in res["done"] and calls == [["1"]]
    assert json.loads((tmp_path / sess[0] / "state.json").read_text())["steps"]["outcomes"]["final"]


def test_stage2_k_and_gate(tmp_path):
    with pytest.raises(c9.NotNow):
        c9.stage2_k(tmp_path)
    (tmp_path / "results_P.json").write_text(json.dumps({"P1": {"advance": True}, "P2": {"advance": False}}))
    (tmp_path / "results_KD.json").write_text(json.dumps({"K1": {"advance": True}, "D1": {"advance": False}}))
    der = c9.stage2_k(tmp_path)
    assert der["k"] == 2 and der["advanced"] == ["P1", "K1"] and c9.stage2_gate(der) == pytest.approx(0.025)
    assert c9.check_stage2_k(None, der) == 2 and c9.check_stage2_k(2, der) == 2
    with pytest.raises(c9.Refused):
        c9.check_stage2_k(3, der)
    with pytest.raises(c9.Refused):
        c9.stage2_gate({"k": 0, "alpha_each": None})


def test_p_stats_use_the_given_gate():
    rng = np.random.default_rng(5)
    units = []
    for d in range(40):
        for tk in range(18):
            units.append({"market_id": f"{d}-{tk}", "day": f"2026-05-{d % 28 + 1:02d}-{d}", "ticker": f"T{tk}", "month": "2026-05", "label": "ok",
                          "trade": {"token": "up", "a": 0.5, "fee": 0.01, "rate": 0.04, "ask_size": 100.0, "edge": 0.06}, "trade_cost": None})
    ys = {u["market_id"]: float(rng.random() < 0.56) for u in units}
    r1 = py.p1_stat(units, lambda u, t: ys[u["market_id"]], n_draws=5, gate_p=0.5)
    r2 = py.p1_stat(units, lambda u, t: ys[u["market_id"]], n_draws=5, gate_p=1e-9)
    assert r2["advance"] is False and r2["robustness"]["ii_top5"]["holds"] is False
    assert r1["placebo_breakeven"]["n_draws"] == 5


def test_pyth_frame_rerun_after_disjointness_stall_stays_stalled(tmp_path):
    root = tmp_path / "cb9"
    c9.write_stall(root / "pyth_frame", c9.STALL_DISJOINTNESS, "q0182 unverified")
    (root / "pyth_frame" / "frame.csv.gz").write_bytes(b"x")  # as left by the stalled first run
    smoke = tmp_path / "smoke.json"
    smoke.write_text(json.dumps({"smoke_version": "cb9-smoke-v2", "criteria": {"yahoo_clock": True, "gamma_paging": True}}))
    m = py.pyth_frame(root, None, rules_sha="x", smoke_path=smoke, exclusion_keys_path=tmp_path / "k.csv.gz", now=c9.T_SEAL_EPOCH + 1)
    assert m["status"] == c9.STALL_DISJOINTNESS and m["status"] != "pyth_frame_complete"
    assert c9.stall_of(root / "pyth_frame")["status"] == c9.STALL_DISJOINTNESS  # the manifest on disk is untouched
