# ruff: noqa: E501
"""CB12-O tests (docs/research_lab/CREATIVE_BATCH_12.md CB12-O): frame templates, settlement dates, anchor (listed-K central difference, bracketing, Phi(d2) and the
convention choice), the collector (one idempotent call, two book reads >= 60 s apart, whitelist, guarded outcomes, missed checkpoints), windows by counts only,
census without outcomes, O1 / O2 decision logic, and the rules part independence."""

from __future__ import annotations

import gzip
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest

from astrolabe.research_lab import cb12_common as c12
from astrolabe.research_lab import cb12_o as o12
from astrolabe.research_lab import cb12_smoke as sm

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_cb12  # noqa: E402

SEAL = Path(__file__).resolve().parents[2] / "docs" / "research_lab" / "seals" / "cb12_rules.json"


def ep(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def _run(argv, capsys) -> tuple[int, dict]:
    code = run_cb12.main(argv)
    out = capsys.readouterr().out.strip().splitlines()
    return code, (json.loads(out[-1]) if out else {})


# =====================================================================================================================================================
# Rules: part O is declared and changes nothing else
# =====================================================================================================================================================


def test_o_part_declared_and_common_m_x_unchanged_against_the_committed_seal():
    seal = json.loads(SEAL.read_text())["parts"]
    for p in ("common", "M", "X"):
        assert c12.rules_part_file_doc(p)["rules_sha256"] == seal[p]["rules_sha256"], p
    d = c12.rules_part_file_doc("O")
    assert d["part_declared"] is True and len(d["rules_sha256"]) == 64
    assert d["rules_sha256"] == seal["O"]["rules_sha256"]  # the committed seal carries the current O code (regenerate the O part when cb12_o.py changes, pre-freeze)
    assert "cb12_o" in d["declared"] and d["declared"]["cb12_o"]["o1"]["floor"] == o12.O1_FLOOR
    fn = {f.__qualname__ for f in c12.part_funcs("O")}
    assert {"anchor", "opt_live_tick", "o1_test", "o2_test", "census_o"} <= fn and "say_frame" not in fn and "x1_test" not in fn


def test_o_part_imports_no_other_family(tmp_path, monkeypatch):
    import importlib

    p = tmp_path / "r.json"
    c12.write_rules(p)
    seen: list[str] = []
    real = importlib.import_module
    monkeypatch.setattr(importlib, "import_module", lambda name, package=None: (seen.append(name), real(name, package))[1])
    assert c12.verify_rules(p, require_committed=False, part="O")
    assert not any(x in n for n in seen for x in ("cb12_m", "cb12_x", "cb12_e", "cb12_f")), seen


# =====================================================================================================================================================
# Frame, calendar
# =====================================================================================================================================================


def test_templates_weekly_and_tickers():
    assert o12.classify_title("NVIDIA (NVDA) closes above ___ on October 21?") == ("daily", "NVDA")
    assert o12.classify_title("S&P 500 (SPY) closes above ___ on November 3?") == ("daily", "SPY")
    assert o12.classify_title("Will Tesla (TSLA) close above ___ end of October?") == ("month_end", "TSLA")
    assert o12.classify_title("Will Micron (MU) close above ___ on October 30?") == ("month_end", "MU")
    assert o12.classify_title("Will Apple (AAPL) finish week of October 23 above ___?")[0] == "weekly"
    assert o12.classify_title("SPY Up or Down on October 21?") == (None, "")
    assert o12.underlying_of("WTI")["excluded"] and o12.underlying_of("VIX")["excluded"]
    assert o12.underlying_of("SPX") == {"excluded": "", "cboe": "_SPX", "root": "SPXW", "yahoo": "^GSPC", "kind": "index"}
    assert o12.underlying_of("NVDA")["cboe"] == "NVDA"


def test_settlement_dates_and_strikes():
    end = ep("2026-10-21T20:00:00Z")
    assert o12.settlement_date("NVIDIA (NVDA) closes above ___ on October 21?", end) == "2026-10-21"
    assert o12.settlement_date("Will Tesla (TSLA) close above ___ end of October?", ep("2026-10-31T20:00:00Z")) == "2026-10-30"  # Oct 31 2026 is a Saturday
    assert o12.settlement_date("X (Y) closes above ___ on January 4?", ep("2027-01-04T21:00:00Z")) == "2027-01-04"  # year closest to the endDate
    assert o12.settlement_date("Will A (B) close above ___ end of December?", ep("2026-12-31T21:00:00Z")) == "2026-12-31"
    assert o12.settlement_date("no date here", end) is None
    assert o12.parse_strike("$1,250.5", "") == 1250.5 and o12.parse_strike("", "Will X close above $180 on October 21?") == 180.0
    assert math.isnan(o12.parse_strike("", "no strike"))


def test_dst_checkpoints_half_sessions_holidays_and_window_start():
    hrs = [datetime.fromtimestamp(t, UTC).hour for _l, t in o12.checkpoint_epochs("2026-10-30")]
    assert hrs == [15, 17, 19]
    assert [datetime.fromtimestamp(t, UTC).hour for _l, t in o12.checkpoint_epochs("2026-11-02")] == [16, 18, 20]
    assert o12.checkpoint_epochs("2026-11-27") == [] and o12.checkpoint_epochs("2026-11-26") == [] and o12.checkpoint_epochs("2026-10-24") == []
    assert o12.is_session("2026-11-27") and not o12.is_regular("2026-11-27")
    assert o12.window1_start(ep("2026-10-19T18:00:00Z")) == "2026-10-20"
    assert o12.window1_start(ep("2026-10-23T18:00:00Z")) == "2026-10-26"  # Friday freeze -> Monday
    assert o12.prev_session("2026-10-26") == "2026-10-23" and o12.next_session("2026-11-25") == "2026-11-27"


def _member(**kw) -> dict:
    m = {"event_id": "e", "market_id": "m1", "condition_id": "c", "token_yes": "ty", "yes_index": 0, "K": 180.0, "settle": "2026-10-21", "template": "daily", "ticker": "NVDA",
         "cboe": "NVDA", "root": "NVDA", "yahoo": "NVDA", "underlying_excluded": "", "end_epoch": ep("2026-10-21T20:00:00Z"), "created_epoch": ep("2026-10-18T00:00:00Z"),
         "closed": False, "neg_risk": True, "fee_rate": 0.04, "desc_sha256": "x", "flags": {}}
    m.update(kw)
    return m


def test_member_status_rules():
    t = ep("2026-10-20T15:00:30Z")
    assert o12.member_status(_member(), "2026-10-20", t) == ""
    assert o12.member_status(_member(underlying_excluded="commodity"), "2026-10-20", t).startswith("excluded")
    assert o12.member_status(_member(settle="2026-10-24"), "2026-10-20", t) == "excluded: settlement not a session"
    assert o12.member_status(_member(settle="2026-10-30"), "2026-10-20", t) == "excluded: settlement date ambiguous"
    assert o12.member_status(_member(settle="2026-10-19", end_epoch=ep("2026-10-19T20:00:00Z")), "2026-10-20", t) == "past settlement"
    assert o12.member_status(_member(created_epoch=t - 600), "2026-10-20", t) == "not listed"
    assert o12.member_status(_member(K=math.nan), "2026-10-20", t) == "excluded: strike unparsed"
    assert o12.member_status(_member(settle="2026-10-20", end_epoch=ep("2026-10-20T20:00:00Z")), "2026-10-20", ep("2026-10-20T20:00:00Z")) == "past settlement"


# =====================================================================================================================================================
# Chain, anchor, convention
# =====================================================================================================================================================


def _chain_doc(ts: str, strikes, mids, *, expiry="261021", root="NVDA", spot=180.0, extra=None) -> dict:
    opts = []
    for k, m in zip(strikes, mids, strict=True):
        for cp, mid in (("C", m), ("P", max(0.05, k - spot + m))):
            opts.append({"option": f"{root}{expiry}{cp}{int(k * 1000):08d}", "bid": round(mid * 0.97, 4), "ask": round(mid * 1.03, 4), "bid_size": 10, "ask_size": 10, "iv": 0.4,
                         "theo": mid, "delta": 0.5, "open_interest": 1, "volume": 1, "last_trade_time": "x", "gamma": 0.1})
    data = {"symbol": root, "current_price": spot, "bid": spot - 0.1, "ask": spot + 0.1, "close": spot, "prev_day_close": spot, "iv30": 40.0, "last_trade_time": "x", "options": opts}
    data.update(extra or {})
    return {"timestamp": ts, "data": data, "symbol": root}


def test_parse_option_and_chain_subset_keeps_three_strikes_each_side_and_expiries():
    assert o12.parse_option("NVDA261019C00120000") == ("NVDA", "2026-10-19", "C", 120.0)
    assert o12.parse_option("SPXW261021P05800000") == ("SPXW", "2026-10-21", "P", 5800.0)
    assert o12.parse_option("bad") is None
    ks = [160.0 + 5 * i for i in range(9)]  # 160..200
    doc = _chain_doc("2026-10-20 14:45:00", ks, [max(0.1, 180 - k + 3) for k in ks])
    sub = o12.chain_subset(doc, "NVDA", [(180.0, "2026-10-21")], 1.0)
    kept = sorted({r[3] for r in sub["options"]})
    assert kept == [165.0, 170.0, 175.0, 180.0, 185.0, 190.0] and sub["expiries"] == ["2026-10-21"] and sub["status"] == "ok"
    assert sub["ts_epoch"] == ep("2026-10-20T14:45:00Z")
    sub2 = o12.chain_subset(doc, "NVDA", [(181.0, "2026-10-21")], 1.0)
    assert sorted({r[3] for r in sub2["options"]}) == [170.0, 175.0, 180.0, 185.0, 190.0, 195.0]
    sub3 = o12.chain_subset(doc, "NVDA", [(180.0, "2026-10-20")], 1.0)  # d not listed -> nearest expiry >= d
    assert {r[2] for r in sub3["options"]} == {"2026-10-21"}
    assert o12.chain_subset({"oops": 1}, "NVDA", [], 1.0)["status"] == "no data"


def test_anchor_direct_central_difference_bracketing_and_phi_d2():
    ks = [170.0, 175.0, 180.0, 185.0, 190.0]
    doc = _chain_doc("2026-10-20 14:45:00", ks, [11.0, 7.0, 4.0, 2.0, 1.0])
    ch = o12.chain_subset(doc, "NVDA", [(180.0, "2026-10-21"), (182.0, "2026-10-21")], 1.0)
    a = o12.anchor(ch, 180.0, "2026-10-21", None)
    assert a["type"] == "direct" and abs(a["q"] - (7.0 - 2.0) / 10.0) < 1e-12 and a["spread_ok"]  # listed K: strikes immediately below and above
    b = o12.anchor(ch, 182.0, "2026-10-21", None)
    assert abs(b["q"] - (4.0 - 2.0) / 5.0) < 1e-12  # unlisted K: the bracketing strikes
    c = o12.anchor(ch, 180.0, "2026-10-20", None)  # no listed expiry equals d -> Phi(d2) needs the convention
    assert c["q"] is None and c["reason"] == "excluded: phi(d2) without convention"
    d = o12.anchor(ch, 180.0, "2026-10-20", "act365")
    assert d["type"] == "phi_d2" and 0.4 < d["q"] < 0.6
    assert o12.anchor(ch, 300.0, "2026-10-21", None)["reason"] == "excluded: no anchor"
    wide = _chain_doc("2026-10-20 14:45:00", ks, [11.0, 7.0, 4.0, 2.0, 1.0])
    for opt in wide["data"]["options"]:
        opt["bid"], opt["ask"] = opt["theo"] * 0.8, opt["theo"] * 1.2
    assert o12.anchor(o12.chain_subset(wide, "NVDA", [(180.0, "2026-10-21")], 1.0), 180.0, "2026-10-21", None)["spread_ok"] is False


def test_time_conventions_and_convention_choice():
    t0 = o12.et_epoch("2026-10-20", 12, 0)
    assert abs(o12.time_to_expiry(t0, "2026-10-21", "act365") - (28 * 3600) / (365 * 86400)) < 1e-12
    assert abs(o12.session_hours(t0, "2026-10-21") - (4.0 + 6.5)) < 1e-9
    assert abs(o12.time_to_expiry(t0, "2026-10-21", "trading_hours") - 10.5 / (252 * 6.5)) < 1e-12
    with pytest.raises(c12.Refused):
        o12.time_to_expiry(t0, "2026-10-21", "nope")

    def chains(conv):
        out = {}
        for j in range(6):
            S, calls = 100.0 + j, []
            for e in ("2026-10-27", "2026-11-06"):
                for k in (S - 2, S - 1, S, S + 1, S + 2):
                    theo = o12.bs_call(S, k, 0.3, o12.time_to_expiry(t0, e, conv))
                    calls.append([f"S{j}", "C", e, k, theo * 0.99, theo * 1.01, None, None, 0.3, theo])
            out[f"S{j}"] = {"underlying": {"current_price": S}, "ts_epoch": t0, "all_calls": calls}
        return out

    r = o12.convention_check(chains("act365"))
    assert r["n_options"] == 20 and r["choice"] == "act365" and r["match_share"]["act365"] == 1.0
    r2 = o12.convention_check(chains("trading_hours"))
    assert r2["choice"] == "trading_hours" and r2["match_share"]["act365"] < 0.8
    assert o12.convention_check({})["choice"] == "none"


def test_exdiv_rule_reads_the_previous_session_nasdaq_file_indices_exempt():
    t = ep("2026-10-20T15:00:00Z")
    prev = {"fetched_t_end": ep("2026-10-19T15:10:00Z"), "dividends": {"AAA": ["2026-10-25"], "BBB": ["2026-11-25"], "CCC": ["2026-10-20"], "DDD": []}}
    assert o12.exdiv_status(prev, "AAA", "AAA", t, "2026-10-30") == "excluded: ex-dividend"
    assert o12.exdiv_status(prev, "BBB", "BBB", t, "2026-10-30") == ""
    assert o12.exdiv_status(prev, "CCC", "CCC", t, "2026-10-30") == ""  # ex-date on the unit's own day: already ex at t
    assert o12.exdiv_status(prev, "DDD", "DDD", t, "2026-10-30") == ""  # a valid empty list = none announced
    assert o12.exdiv_status(prev, "EEE", "EEE", t, "2026-10-30") == "excluded: ex-dividend unknown"  # not in the previous file
    assert o12.exdiv_status(None, "AAA", "AAA", t, "2026-10-30") == "excluded: ex-dividend unknown"  # no previous file
    assert o12.exdiv_status({**prev, "fetched_t_end": t + 1}, "BBB", "BBB", t, "2026-10-30") == "excluded: ex-dividend unknown"  # a file fetched after t is never used
    assert o12.exdiv_status(None, "SPX", "_SPX", t, "2026-10-30") == ""  # cash-settled index: exempt


def test_dividend_fetch_asset_class_etf_list_and_fallback():
    calls = []

    class S:
        def dividends(self, sym, kind):
            calls.append((sym, kind))
            ok = (kind == "etf") == (sym in ("SPY", "ZETF"))
            return {"data": {"dividends": {"rows": [{"exOrEffDate": "12/19/2026"}]}}} if ok else {"data": None, "status": {"rCode": 400}}

    assert o12.fetch_dividends(S(), "SPY") == ["2026-12-19"] and calls == [("SPY", "etf")]  # frozen ETF list: no stocks query
    calls.clear()
    assert o12.fetch_dividends(S(), "AAPL") == ["2026-12-19"] and calls == [("AAPL", "equity")]
    calls.clear()
    assert o12.fetch_dividends(S(), "ZETF") == ["2026-12-19"] and calls == [("ZETF", "equity"), ("ZETF", "etf")]  # unknown ETF: stocks first, then etf
    with pytest.raises(o12.cm.ApiError):
        o12.fetch_dividends(type("X", (), {"dividends": lambda self, s_, k: {"data": None}})(), "NOPE")


def test_earnings_flag_window():
    t = o12.et_epoch("2026-10-20", 11, 0)
    f = t - 60.0  # the file was fetched before t
    rows = [["2026-10-20", "NVDA", "time-pre-market"]]
    assert o12.earnings_flag(rows, "NVDA", t, "2026-10-22", "2026-10-22", f) is False  # released before t
    assert o12.earnings_flag([["2026-10-20", "NVDA", "time-after-hours"]], "NVDA", t, "2026-10-22", "2026-10-22", f) is True
    assert o12.earnings_flag([["2026-10-22", "NVDA", "time-after-hours"]], "NVDA", t, "2026-10-22", "2026-10-22", f) is False  # after the settlement close
    assert o12.earnings_flag([["2026-10-22", "NVDA", "time-pre-market"]], "NVDA", t, "2026-10-22", "2026-10-22", f) is True
    assert o12.earnings_flag([["2026-10-21", "NVDA", "time-not-supplied"]], "NVDA", t, "2026-10-22", "2026-10-22", f) is True
    assert o12.earnings_flag([["2026-10-21", "AMD", ""]], "NVDA", t, "2026-10-22", "2026-10-22", f) is False
    assert o12.earnings_flag(None, "NVDA", t, "2026-10-22", "2026-10-22", f) is None
    # amendment O4: the file's calendar must reach the settlement date, else unknown (never False)
    assert o12.earnings_flag(rows, "NVDA", t, "2026-10-22", "2026-10-21", f) is None
    assert o12.earnings_flag(rows, "NVDA", t, "2026-10-22", None, f) is None
    assert o12.earnings_flag([["2026-10-21", "NVDA", ""]], "NVDA", t, "2026-10-22", "2026-10-30", f) is True
    # amendment O5: the function checks the file's causality itself
    after = [["2026-10-21", "NVDA", ""]]
    assert o12.earnings_flag(after, "NVDA", t, "2026-10-22", "2026-10-22", f) is True
    for bad in (t, t + 5.0, None, math.nan):
        assert o12.earnings_flag(after, "NVDA", t, "2026-10-22", "2026-10-22", bad) is None
    assert o12.earnings_flag(after, "NVDA", t, "2026-10-22", "2026-10-22") is None


def test_daily_file_age_days_disclosed_after_a_missed_daily_step():
    assert o12.daily_age_days("2026-10-20", "2026-10-21") == 1
    assert o12.daily_age_days("2026-10-20", "2026-10-23") == 3  # outage: an older file is used
    assert o12.daily_age_days(None, "2026-10-23") is None


def test_realised_vol_uses_only_bars_before_the_day():
    closes = [(f"2026-09-{d:02d}", 100.0 * (1.01 ** (d % 2))) for d in range(1, 26)] + [("2026-10-20", 1e6)]
    v = o12.realised_vol(closes, "2026-10-20")
    assert math.isfinite(v) and v < 1.0  # the huge bar on the unit's day is not used
    assert math.isnan(o12.realised_vol(closes[:10], "2026-10-20"))


def test_window_bounds_close_on_counts_only():
    sess = o12.sessions_between("2026-10-20", "2027-01-29")
    tight = {d: {"A", "B"} for d in sess[:40]}
    w = o12.window_bounds(tight, "2026-10-20", "2027-03-01", o12.WINDOW1_CAP)
    assert w["closed"] and w["end"] == sess[29] and w["dates"] == 30 and w["clusters"] == 60  # 30 dates x 2 tickers
    w_open = o12.window_bounds(tight, "2026-10-20", sess[10], o12.WINDOW1_CAP)
    assert not w_open["closed"] and w_open["dates"] == 10
    thin = {d: {"A"} for d in sess[:20]}
    w_cap = o12.window_bounds(thin, "2026-10-20", "2027-03-01", o12.WINDOW1_CAP)
    assert w_cap["closed"] and w_cap["by"] == "cap" and not w_cap["power_ok"]
    with pytest.raises(c12.NotNow):
        o12.window_dates(w_open)


# =====================================================================================================================================================
# The collector, end to end with fake sources
# =====================================================================================================================================================


class _Lim:
    def __init__(self):
        self.requests = 0


class FakeSrc:
    """A fake ``Sources``: a controllable clock, one daily NVDA event (3 strikes) and one month-end TSLA event, CBOE chains 15 min old, two-sided books."""

    def __init__(self, t: float):
        self.t = t
        self.pm, self.ext = _Lim(), _Lim()
        self.book_calls: list[tuple[str, float]] = []
        self.secret = "SECRETDESC-PLEASE-NOT-STORED"

    def clock(self) -> float:
        return self.t

    def sleep(self, s: float) -> None:
        self.t += s

    def _mk(self, mid, k):
        return {"id": mid, "conditionId": f"c{mid}", "outcomes": '["Yes", "No"]', "clobTokenIds": json.dumps([f"y{mid}", f"n{mid}"]), "groupItemTitle": f"${k}",
                "question": f"q {k}", "endDate": "2026-10-21T20:00:00Z", "createdAt": "2026-10-18T00:00:00Z", "outcomePrices": '["0.123456", "0.876544"]', "bestBid": 0.777,
                "lastTradePrice": 0.666, "negRisk": True, "feeSchedule": {"rate": 0.04}, "description": f"Resolves per Pyth close. {self.secret}", "closed": False}

    def search(self, q, page):
        self.pm.requests += 1
        if q == "closes above":
            ev = {"id": "e1", "title": "NVIDIA (NVDA) closes above ___ on October 21?", "markets": [self._mk(f"m{k}", k) for k in (175, 180, 185)]}
            wk = {"id": "e3", "title": "Will NVIDIA (NVDA) finish week of October 23 above ___?", "markets": []}
            return {"events": [ev, wk], "pagination": {"hasMore": False}}
        tsla = {"id": "e2", "title": "Will Tesla (TSLA) close above ___ end of October?", "markets": [dict(self._mk("t1", 400), endDate="2026-10-30T20:00:00Z")]}
        oil = {"id": "e4", "title": "WTI Crude Oil (WTI) closes above ___ on October 21?", "markets": [self._mk("w1", 90)]}
        return {"events": [tsla, oil], "pagination": {"hasMore": False}}

    def chain(self, sym):
        self.ext.requests += 1
        self.t += 1.0
        ts = datetime.fromtimestamp(self.t - 900, UTC).strftime("%Y-%m-%d %H:%M:%S")
        if sym == "NVDA":
            return 200, _chain_doc(ts, [170.0, 175.0, 180.0, 185.0, 190.0], [11.0, 7.0, 4.0, 2.0, 1.0], extra={"next_dividend_date": "2026-12-10"}), self.t
        return 200, _chain_doc(ts, [390.0, 400.0, 410.0], [15.0, 9.0, 5.0], expiry="261030", root="TSLA", spot=400.0), self.t

    def book(self, token):
        self.pm.requests += 1
        self.t += 0.5
        self.book_calls.append((token, self.t))
        return {"bids": [{"price": "0.48", "size": "100"}, {"price": "0.47", "size": "50"}], "asks": [{"price": "0.51", "size": "80"}], "timestamp": "1", "tick_size": "0.001"}, self.t

    def yahoo_daily(self, sym, p1, p2):
        self.ext.requests += 1
        days = [d for d in o12.sessions_between("2026-08-01", "2026-12-31") if p1 <= o12.et_epoch(d, 9, 30) < p2]
        return {"chart": {"result": [{"timestamp": [int(o12.et_epoch(d, 9, 30)) for d in days], "indicators": {"quote": [{"close": [100.0 + i % 3 for i in range(len(days))]}]}}]}}

    def earnings(self, day):
        self.ext.requests += 1
        return {"data": {"rows": [{"symbol": "NVDA", "time": "time-after-hours", "epsForecast": "$1"}, {"symbol": "ZZZ", "time": ""}]}}

    def dividends(self, sym, kind):
        self.ext.requests += 1
        return {"data": {"dividends": {"rows": [{"exOrEffDate": "12/10/2026", "amount": "$0.01"}]}}}

    def gamma_markets(self, ids):
        self.pm.requests += 1
        return [{"id": i, "closed": True, "outcomePrices": '["1", "0"]', "umaResolutionStatus": "resolved", "bestBid": 0.9} for i in ids]


def _gz_text(p: Path) -> str:
    return gzip.decompress(p.read_bytes()).decode()


@pytest.fixture()
def oroot(tmp_path):
    return tmp_path / "history" / "h12_opt_live"


FROZEN = ep("2026-10-19T12:00:00Z")


def test_collector_checkpoint_daily_outcomes_missed_and_whitelist(oroot):
    t = o12.et_epoch("2026-10-20", 11, 0) + 30
    src = FakeSrc(t)
    r = o12.opt_live_tick(oroot, now=t, src=src, rules_sha="r" * 64, frozen_epoch=FROZEN, sleep=src.sleep)
    assert r["status"] == "checkpoint" and r["checkpoint"] == "1100" and r["n_members"] == 4 and r["n_chains"] == 2
    raw = oroot / "raw" / "2026-10-20" / "1100.json.gz"
    rec = json.loads(_gz_text(raw))
    assert rec["member_reasons"].get("event excluded: weekly") == 1 and any(k.startswith("excluded: commodity") for k in rec["member_reasons"])
    assert sorted(m["market_id"] for m in rec["members"]) == ["m175", "m180", "m185", "t1"]
    txt = _gz_text(raw)
    for bad in (src.secret, "0.123456", "0.777", "0.666", "outcomePrices", "bestBid", "lastTradePrice", "proxyWallet"):
        assert bad not in txt, bad
    first = {}
    for tok, ts in src.book_calls:  # the second read of each member is >= 60 s after its first; every chain was read before the first book
        if tok in first:
            assert ts - first[tok] >= o12.BOOK_GAP_S
        else:
            first[tok] = ts
    assert all(len(v) == 2 for v in rec["books"].values())
    assert all(rec["chains"][s]["receipt_t"] < min(first.values()) for s in rec["chains"])
    man = json.loads((oroot / "manifest.json").read_text())
    assert "raw/2026-10-20/1100.json.gz" in man["file_sha256"] and man["requests"] > 0
    # same checkpoint window again: nothing re-done; then the daily step; then the outcome step (nothing settled yet)
    assert o12.opt_live_tick(oroot, now=t + 300, src=src, rules_sha="r" * 64, frozen_epoch=FROZEN)["status"] == "daily"
    daily = json.loads(_gz_text(oroot / "daily" / "2026-10-20.json.gz"))
    assert daily["earnings"] and all(r[1] == "NVDA" for r in daily["earnings"]) and daily["dividends"]["NVDA"] == ["2026-12-10"]
    assert all(d < "2026-10-20" for d, _c in daily["yahoo"]["NVDA"])  # features: bars before the day only
    assert o12.opt_live_tick(oroot, now=t + 600, src=src, rules_sha="r" * 64, frozen_epoch=FROZEN) == {"status": "outcomes", "dates": []}
    # 13:00 window missed entirely -> unavailable (collection), never back-filled
    o12.opt_live_tick(oroot, now=o12.et_epoch("2026-10-20", 13, 25), src=src, rules_sha="r" * 64, frozen_epoch=FROZEN)
    st = json.loads((oroot / "state.json").read_text())
    assert st["days"]["2026-10-20"]["ckpt"]["1300"]["status"] == "unavailable (collection)"
    assert not (oroot / "raw" / "2026-10-20" / "1300.json.gz").exists()
    # after settlement (Oct 21): guarded outcome files only
    t2 = o12.et_epoch("2026-10-22", 12, 0)
    r2 = o12.opt_live_tick(oroot, now=t2, src=FakeSrc(t2), rules_sha="r" * 64, frozen_epoch=FROZEN)
    assert r2["status"] == "outcomes" and r2["dates"] == ["2026-10-21"]
    g = oroot / "outcomes_guarded" / "2026-10-21"
    assert (g / "gamma.csv.gz").exists() and (g / "yahoo_close.csv.gz").exists()
    st = json.loads((oroot / "state.json").read_text())
    assert st["outcomes"]["2026-10-21"]["final"] is True
    assert "0.9" not in _gz_text(g / "gamma.csv.gz").split("\n", 1)[1].split(",")[-1]  # bestBid of the reply is not kept


def test_collector_refuses_before_freeze_disk_refusal_is_a_counted_unit_and_busy_lock(oroot):
    t = o12.et_epoch("2026-10-20", 11, 0) + 30
    with pytest.raises(c12.Refused, match="after the O freeze"):
        o12.opt_live_tick(oroot, now=t, src=FakeSrc(t), rules_sha="r", frozen_epoch=t + 1)

    def full():
        raise c12.NotNow("disk")

    r = o12.opt_live_tick(oroot, now=t, src=FakeSrc(t), rules_sha="r", frozen_epoch=FROZEN, disk_check=full)
    assert r["status"] == "checkpoint_unavailable_disk"
    st = json.loads((oroot / "state.json").read_text())
    assert st["days"]["2026-10-20"]["ckpt"]["1100"]["status"] == "unavailable (host disk)"
    import fcntl

    with open(oroot / ".lock", "w") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        assert o12.opt_live_tick(oroot, now=t, src=FakeSrc(t), rules_sha="r", frozen_epoch=FROZEN)["status"] == "busy"
    with pytest.raises(c12.Refused):
        o12.opt_live_tick(Path("/tmp/creative_batch11/h12_opt_live"), now=t, src=FakeSrc(t), rules_sha="r", frozen_epoch=FROZEN)


def _prev_daily(oroot, *, nvda_divs, symbols=("NVDA",), day="2026-10-19", covered_end="2026-10-30"):
    o12._wjson_gz(oroot / "daily" / f"{day}.json.gz", {"day": day, "earnings_covered_end": covered_end, "yahoo": {}, "earnings": [["2026-10-21", "NVDA", "time-after-hours"]], "earnings_symbols": list(symbols),
                                                     "dividends": {"NVDA": nvda_divs}, "errors": [], "fetched_t_start": ep("2026-10-19T15:00:00Z"), "fetched_t_end": ep("2026-10-19T15:05:00Z")})


def test_build_units_labels_and_exdiv_from_the_previous_session_file(oroot):
    t = o12.et_epoch("2026-10-20", 11, 0) + 30
    src = FakeSrc(t)
    o12.opt_live_tick(oroot, now=t, src=src, rules_sha="r", frozen_epoch=FROZEN, sleep=src.sleep)
    units, ck = o12.build_units(oroot, ["2026-10-21", "2026-10-30"], None)  # no previous-session file at all: every equity unit is unknown (counted)
    assert {u["label"] for u in units} == {"excluded: ex-dividend unknown"}
    _prev_daily(oroot, nvda_divs=["2026-12-10"])
    units, ck = o12.build_units(oroot, ["2026-10-21", "2026-10-30"], None)
    lab = {u["market_id"]: u["label"] for u in units}
    assert ck["files"] == 1
    assert lab["m180"] == "available" and lab["m175"] == "available"  # NVDA: the previous file's ex-date is outside (t, d]
    assert lab["t1"] == "excluded: ex-dividend unknown"  # TSLA has no entry in the previous file
    u = next(x for x in units if x["market_id"] == "m180")
    assert u["anchor_type"] == "direct" and abs(u["q"] - 0.5) < 1e-9 and abs(u["m1"] - 0.495) < 1e-9 and u["m2"] == u["m1"] and "y" not in u
    assert u["o2_ok"] is True and u["earnings"] is False  # earnings from the PREVIOUS file (NVDA in its symbols); the after-hours Oct 21 row is not before d = Oct 21
    assert o12.tight_by_date(oroot) == {"2026-10-21": {"NVDA"}, "2026-10-30": {"TSLA"}}
    _prev_daily(oroot, nvda_divs=["2026-10-21"])
    units, _ = o12.build_units(oroot, ["2026-10-21"], None)
    assert {u["label"] for u in units} == {"excluded: ex-dividend"}


def test_earnings_beyond_the_previous_files_covered_end_is_unknown(oroot):
    t = o12.et_epoch("2026-10-20", 11, 0) + 30
    src = FakeSrc(t)
    o12.opt_live_tick(oroot, now=t, src=src, rules_sha="r", frozen_epoch=FROZEN, sleep=src.sleep)
    _prev_daily(oroot, nvda_divs=[], covered_end="2026-10-21")  # calendar read only up to Oct 21
    units, _ = o12.build_units(oroot, ["2026-10-21"], None)
    assert next(x for x in units if x["market_id"] == "m180")["earnings"] is False
    _prev_daily(oroot, nvda_divs=[], covered_end="2026-10-20")  # a member settling Oct 21 is beyond it
    units, _ = o12.build_units(oroot, ["2026-10-21"], None)
    assert next(x for x in units if x["market_id"] == "m180")["earnings"] is None


def test_run_daily_records_the_earnings_covered_end(oroot):
    t = o12.et_epoch("2026-10-20", 11, 0) + 30
    src = FakeSrc(t)
    o12.opt_live_tick(oroot, now=t, src=src, rules_sha="r", frozen_epoch=FROZEN, sleep=src.sleep)
    o12.opt_live_tick(oroot, now=t + 300, src=src, rules_sha="r", frozen_epoch=FROZEN, sleep=src.sleep)
    daily = json.loads(_gz_text(oroot / "daily" / "2026-10-20.json.gz"))
    assert daily["earnings_covered_end"] == "2026-10-30"  # the last settlement date of the day's members (no fetch failed)


def test_day_after_a_half_session_reads_the_latest_earlier_daily_file():
    # 2026-11-27 is a half session (no checkpoints, no daily file): Mon 2026-11-30 must read the last file before it (Wed 2026-11-25)
    assert o12.prev_session("2026-11-30") == "2026-11-27"
    daily = {"2026-11-24": {"day": "2026-11-24"}, "2026-11-25": {"day": "2026-11-25"}}
    assert o12.previous_daily(daily, "2026-11-30")["day"] == "2026-11-25"
    assert o12.previous_daily(daily, "2026-11-25")["day"] == "2026-11-24"  # strictly before the day
    assert o12.previous_daily(daily, "2026-11-24") is None
    assert o12.previous_daily({"2026-12-01": {"day": "x"}}, "2026-11-30") is None  # never a later file
    # the status of a 2026-11-30 unit: a real answer from the 2026-11-25 file, not 'unknown'
    full = {"2026-11-25": {"fetched_t_end": ep("2026-11-25T21:00:00Z"), "dividends": {"NVDA": []}}}
    t = o12.et_epoch("2026-11-30", 11, 0)
    assert o12.exdiv_status(o12.previous_daily(full, "2026-11-30"), "NVDA", "NVDA", t, "2026-12-02") == ""


def test_census_opens_no_outcome_and_waits_for_window_and_outcomes(oroot, monkeypatch):
    t = o12.et_epoch("2026-10-20", 11, 0) + 30
    src = FakeSrc(t)
    o12.opt_live_tick(oroot, now=t, src=src, rules_sha="r", frozen_epoch=FROZEN, sleep=src.sleep)
    _prev_daily(oroot, nvda_divs=[])
    with pytest.raises(c12.NotNow):
        o12.census_o(oroot, {"closed": False}, None)
    win = {"start": "2026-10-20", "end": "2026-10-30", "closed": True, "power_ok": False}
    with pytest.raises(c12.NotNow, match="outcome step not final"):
        o12.census_o(oroot, win, None)
    st = json.loads((oroot / "state.json").read_text())
    st["outcomes"] = {"2026-10-21": {"final": True}, "2026-10-30": {"final": True}}
    (oroot / "state.json").write_text(json.dumps(st))

    def boom(*a, **k):
        raise AssertionError("census opened an outcome file")

    monkeypatch.setattr(o12, "open_outcomes", boom)
    c = o12.census_o(oroot, win, None)
    assert c["counts_only"] and c["label_O"] == "not run (power)" and c["GO"]["tight_units"] == 3 and "y" not in json.dumps(c["by_ticker"])
    # item 8: the window's scheduled checkpoints are 3 per regular session; only the 2026-10-20 11:00 one was collected, the 13:00 / 15:00 windows have not passed (not recorded)
    assert c["collection"]["ok"] == 1 and c["collection"]["scheduled"] == 3 * len(o12.sessions_between("2026-10-20", "2026-10-30"))
    assert 0 < c["collection"]["share"] < 1 and c["availability_share_incl_missed_checkpoints"] <= c["availability_share"]


def test_outcome_accessor_job_and_window_guard(oroot):
    for job, win in (("census", "w1"), ("screen-O", "w2"), ("rep-O", "w1"), ("screen-M", "w1")):
        with pytest.raises(c12.Refused):
            o12.open_outcomes(oroot, [], job, win, frozen_epoch=FROZEN)
    with pytest.raises(c12.Refused, match="freeze epoch"):
        o12.open_outcomes(oroot, [], "screen-O", "w1")
    t = o12.et_epoch("2026-10-20", 11, 0) + 30
    src = FakeSrc(t)
    o12.opt_live_tick(oroot, now=t, src=src, rules_sha="r", frozen_epoch=FROZEN, sleep=src.sleep)
    now = ep("2027-02-03T12:00:00Z")  # past the window-1 cap: the window is closed
    w1 = o12.windows(oroot, FROZEN, now)["w1"]
    dates = o12.window_dates(w1)
    assert o12.open_outcomes(oroot, dates[:2], "screen-O", "w1", frozen_epoch=FROZEN, now=now) == ({}, {})
    with pytest.raises(c12.Refused, match="outside w1"):
        o12.open_outcomes(oroot, [*dates[:2], "2027-02-02"], "screen-O", "w1", frozen_epoch=FROZEN, now=now)  # a date beyond the recomputed window
    with pytest.raises(c12.NotNow):  # window 2 is not closed at this time: its outcomes cannot be opened
        o12.open_outcomes(oroot, [dates[0]], "rep-O", "w2", frozen_epoch=FROZEN, now=now)
    with pytest.raises(c12.NotNow):
        o12.open_outcomes(oroot, dates[:1], "screen-O", "w1", frozen_epoch=FROZEN, now=ep("2026-10-25T12:00:00Z"))  # window 1 not closed yet


def _screen_root(oroot):
    """A collector root with one 2026-10-20 11:00 checkpoint, the previous session's file, and settled (guarded) outcomes."""
    t = o12.et_epoch("2026-10-20", 11, 0) + 30
    src = FakeSrc(t)
    o12.opt_live_tick(oroot, now=t, src=src, rules_sha="r", frozen_epoch=FROZEN, sleep=src.sleep)
    _prev_daily(oroot, nvda_divs=[])
    for tn in (o12.et_epoch("2026-10-22", 12, 0), o12.et_epoch("2026-11-02", 12, 0)):
        o12.opt_live_tick(oroot, now=tn, src=FakeSrc(tn), rules_sha="r", frozen_epoch=FROZEN)
    return ep("2027-02-03T12:00:00Z")


def test_screen_o_end_to_end_on_the_census_window_dict(oroot):
    now = _screen_root(oroot)
    win = o12.windows(oroot, FROZEN, now)["w1"]
    census = {"window": win, "label_O": None, "cor_q_qrv": 0.3, "collection": o12.collection_counts(oroot, win)}  # census["window"] IS the w1 dict (defect 2)
    r = o12.screen_o(oroot, census, None, earnings_identified=True, frozen_epoch=FROZEN, now=now)
    assert set(r) == {"O1", "O2", "label", "census_label"} and r["census_label"] is None
    assert r["O1"]["test"] == "O1" and r["O2"]["test"] == "O2" and r["O1"]["advance"] is False and r["O2"]["advance"] is False
    assert r["O1"]["checkpoint_share"] == census["collection"]["share"]
    lab = o12.screen_o(oroot, {**census, "label_O": "not run (power)"}, None, earnings_identified=True, frozen_epoch=FROZEN, now=now)
    assert lab["O1"]["verdict"] == "not run (power)"
    log = (oroot / "ACCESS_LOG.jsonl").read_text()
    assert "screen-O" in log and "outcomes_guarded/2026-10-21/" in log


def test_o2_eligibility_does_not_need_the_second_read_and_o1_does():
    us = _world(True)
    for u in us:
        u["label"], u["m2"], u["m2_raw"] = "unavailable (second read)", None, None  # the second read failed everywhere
    tr = o12.o2_trades(us)
    assert tr and all(t["net"] is not None for t in tr)  # O2 still trades on first-read tightness + valid anchor
    assert o12.availability(us, "y_gamma", o2=True) == 1.0 and o12.availability(us, "y") == 0.0
    assert o12.o1_test(us, earnings_identified=False, placebo=False)["verdict"] == "not testable (availability)"
    assert o12.o2_test(us)["testable"] is True


def test_build_units_o2_ok_survives_a_missing_second_read(oroot):
    t = o12.et_epoch("2026-10-20", 11, 0) + 30
    src = FakeSrc(t)
    o12.opt_live_tick(oroot, now=t, src=src, rules_sha="r", frozen_epoch=FROZEN, sleep=src.sleep)
    _prev_daily(oroot, nvda_divs=[])
    p = oroot / "raw" / "2026-10-20" / "1100.json.gz"
    rec = json.loads(_gz_text(p))
    rec["books"]["m180"][1] = {"ok": False, "receipt_t": t + 99}
    o12._wjson_gz(p, rec)
    units, _ = o12.build_units(oroot, ["2026-10-21"], None)
    u = next(x for x in units if x["market_id"] == "m180")
    assert u["label"] == "unavailable (second read)" and u["o2_ok"] is True and u["m2_raw"] is None and "q" in u


def test_mprev_is_the_raw_second_read_of_the_previous_checkpoint_whatever_its_label():
    base = {"market_id": "m", "label": "excluded: q range"}
    us = [{**base, "day": "2026-10-19", "ckpt": "1500", "m2_raw": 0.41}, {**base, "day": "2026-10-20", "ckpt": "1100", "m2_raw": 0.52},
          {**base, "day": "2026-10-20", "ckpt": "1300", "m2_raw": None}, {**base, "day": "2026-10-20", "ckpt": "1500", "m2_raw": 0.6}]
    o12.attach_mprev(us)
    assert [u["m_prev"] for u in us] == [None, 0.41, 0.52, None]  # a checkpoint without a two-sided second read gives no m_prev; labels are irrelevant


def test_gamma_rows_not_yet_resolved_are_asked_again(oroot):
    t = o12.et_epoch("2026-10-20", 11, 0) + 30
    src = FakeSrc(t)
    o12.opt_live_tick(oroot, now=t, src=src, rules_sha="r", frozen_epoch=FROZEN, sleep=src.sleep)
    calls = []

    class G(FakeSrc):
        def gamma_markets(self, ids):
            calls.append(list(ids))
            ok = len(calls) > 1
            return [{"id": i, "closed": True, "outcomePrices": '["1", "0"]' if ok else '["0.5", "0.5"]', "umaResolutionStatus": "resolved" if ok else "proposed"} for i in ids]

    t2 = o12.et_epoch("2026-10-22", 12, 0)
    g = G(t2)
    o12.opt_live_tick(oroot, now=t2, src=g, rules_sha="r", frozen_epoch=FROZEN)
    st = json.loads((oroot / "state.json").read_text())
    assert st["outcomes"]["2026-10-21"]["final"] is False and st["outcomes"]["2026-10-21"]["unresolved"] >= 1
    o12.opt_live_tick(oroot, now=t2 + 4 * 3600, src=g, rules_sha="r", frozen_epoch=FROZEN)
    st = json.loads((oroot / "state.json").read_text())
    assert len(calls) >= 2 and st["outcomes"]["2026-10-21"]["final"] is True


def test_yahoo_gamma_agreement_is_per_market_and_root_cap_refuses_a_checkpoint(oroot):
    us = _world(True)
    for u in us:
        u["y_gamma"] = u["y"]
    wrong = next(u["market_id"] for u in us)
    for u in us:
        if u["market_id"] == wrong:
            u["y_gamma"] = 1.0 - u["y"]  # one market (three units) disagrees
    r = o12.o1_test(us, earnings_identified=True, placebo=False)
    n_mk = len({u["market_id"] for u in us})
    assert r["gamma_agreement"]["n"] == n_mk and abs(r["gamma_agreement"]["share"] - (n_mk - 1) / n_mk) < 1e-12
    t = o12.et_epoch("2026-10-20", 11, 0) + 30
    fs = FakeSrc(t)
    out = o12.opt_live_tick(oroot, now=t, src=fs, rules_sha="r", frozen_epoch=FROZEN, root_cap_bytes=0, sleep=fs.sleep)
    assert out["status"] == "checkpoint"  # an empty root is within a zero cap
    t3 = o12.et_epoch("2026-10-20", 13, 0) + 30
    out = o12.opt_live_tick(oroot, now=t3, src=FakeSrc(t3), rules_sha="r", frozen_epoch=FROZEN, root_cap_bytes=10)
    assert out["status"] == "checkpoint_unavailable_disk"
    assert json.loads((oroot / "state.json").read_text())["days"]["2026-10-20"]["ckpt"]["1300"]["status"] == "unavailable (host disk)"


def test_attribution_uses_the_census_correlation_in_the_screen():
    us = _world(True)
    r = o12.o1_attribution(us, census_cor=0.95, use_census_cor=True)
    assert r["label"] == "not identifiable" and r["cor_source"] == "census"
    r2 = o12.o1_attribution(us, census_cor=None, use_census_cor=True)
    assert r2["label"] == "not identifiable"
    assert o12.o1_attribution(us)["cor_source"] in ("tested units",)


def test_rule_flags_are_declared_descriptive_and_the_cron_file():
    d = o12.declared()
    assert "DESCRIPTIVE ONLY" in d["frame"]["rule_flags_use"]
    cron = (Path(__file__).resolve().parents[2] / "scripts" / "oracle" / "cb12_o_crontab.txt").read_text()
    line = next(x for x in cron.splitlines() if x and not x.startswith("#"))
    assert " timeout " in line and "run_cb12.py opt-live" in line and "--disk-cap-gb 0.3" in line and "flock -n" in line


def test_gamma_yes_mapping():
    assert o12.gamma_yes({"outcome_prices": "[1, 0]", "yes_index": 0, "uma_status": "resolved"}) == 1.0
    assert o12.gamma_yes({"outcome_prices": "[1, 0]", "yes_index": 1, "uma_status": "resolved"}) == 0.0
    assert o12.gamma_yes({"outcome_prices": "[0.5, 0.5]", "yes_index": 0, "uma_status": "resolved"}) == 0.5
    assert o12.gamma_yes({"outcome_prices": "[1, 0]", "yes_index": 0, "uma_status": "proposed"}) is None
    assert o12.gamma_yes(None) is None


# =====================================================================================================================================================
# O1 / O2 decision logic on synthetic worlds
# =====================================================================================================================================================


def _world(informative: bool, seed: int = 7, n_dates: int = 60) -> list[dict]:
    rng = np.random.default_rng(seed)
    dates = o12.sessions_between("2026-10-20", "2027-01-29")[:n_dates]
    units = []
    for d in dates:
        for tk in ("A", "B", "C", "D"):
            pi = float(rng.uniform(0.35, 0.65))
            bias = float(rng.choice([-0.3, 0.3]))
            y = float(rng.random() < pi)
            m = pi - bias if informative else pi
            q = pi if informative else float(np.clip(pi + rng.normal(0, 0.1), 0.06, 0.94))
            for ck in ("1100", "1300", "1500"):
                units.append({"market_id": f"{tk}{d}", "event_id": "e", "ticker": tk, "settle": d, "day": d, "ckpt": ck, "t": o12.et_epoch(d, int(ck[:2])), "K": 1.0,
                              "yes_index": 0, "template": "daily", "fee_rate": 0.04, "yahoo": tk, "cluster": f"{tk}|{d}", "label": "available", "anchor_type": "direct",
                              "m1": m, "m2": m, "m2_raw": m, "o2_ok": True, "a_yes": m + 0.01, "b_yes": m - 0.01, "ask_size": 50.0, "bid_size": 50.0, "q": q, "q_rv": 0.5 + float(rng.normal(0, 0.2)),
                              "earnings": False, "y": y, "y_gamma": y})
    o12.attach_mprev(units)
    return units


def test_o1_advances_in_an_informative_world_and_not_in_a_null_world():
    r = o12.o1_test(_world(True), earnings_identified=True)
    assert r["testable"] and r["beta"] > o12.O1_FLOOR and r["p"] < 0.005 and r["robustness_ok"] and r["placebo"]["holds"] and r["advance"]
    assert r["attribution"]["label"] in ("option-implied", "not option-implied", "not identifiable")
    n = o12.o1_test(_world(False), earnings_identified=False, placebo=False)
    assert not n["advance"] and "earnings not identified" in n["earnings"]


def test_o1_availability_rule_and_units_rule():
    us = _world(True)
    for u in us[: int(len(us) * 0.5)]:
        u["label"] = "unavailable (second read)"
    assert o12.o1_test(us, earnings_identified=False, placebo=False)["verdict"] == "not testable (availability)"
    few = _world(True, n_dates=5)
    assert o12.o1_test(few, earnings_identified=False, placebo=False)["advance"] is False


def test_o2_trades_first_qualifying_checkpoint_fee_and_gamma_payoff():
    us = _world(True)
    tr = o12.o2_trades(us)
    assert len({t["market_id"] for t in tr}) == len(tr) and all(t["ckpt"] == "1100" for t in tr)
    t0 = next(t for t in tr if t["side"] == "yes")
    assert abs(t0["net"] - (t0["y_gamma"] - t0["a"] - 0.04 * t0["a"] * (1 - t0["a"]))) < 1e-12
    t1 = next(t for t in tr if t["side"] == "no")
    assert abs(t1["a"] - (1 - t1["b_yes"])) < 1e-12 and abs(t1["net"] - ((1 - t1["y_gamma"]) - t1["a"] - 0.04 * t1["a"] * (1 - t1["a"]))) < 1e-12
    r = o12.o2_test(us)
    assert r["testable"] and r["net_per_share"] > o12.O2_FLOOR and r["placebo"]["holds"] and r["advance"]
    unresolved = _world(True)
    for u in unresolved:
        u["y_gamma"] = None
    assert o12.o2_test(unresolved)["verdict"] == "not testable (availability)"


def test_o2_mprev_placebo_blocks_a_mid_reversal_world():
    us = _world(True)
    for u in us:  # the previous-checkpoint mid carries the same information as q: the placebo must trade and win, so O2 cannot advance
        u["m_prev"] = u["q"]
    r = o12.o2_test(us)
    assert r["placebo"]["holds"] is False and r["advance"] is False


# =====================================================================================================================================================
# Smoke and runner
# =====================================================================================================================================================


def test_smoke_offline_and_online_with_fake_sources():
    t = o12.et_epoch("2026-10-20", 12, 0)
    src = FakeSrc(t)
    crit, detail = sm.collect_checks(("O",), {"o_sources": src}, src.pm)
    assert crit["guards_fixture_O"] and crit["o_frame_regex"] and crit["o_chain"] and crit["o_chain_timestamp"] and crit["o_books"]
    assert detail["O"]["o_frame_regex"]["templates"]["daily"] == 2 and detail["O"]["o_frame_regex"]["templates"]["weekly"] == 1
    assert crit["o_chain_dividend_field"] is True and crit["o_earnings_keyless"] is True
    assert crit["o_dividends_keyless"] is True and all(v["n_dates"] >= 1 for v in detail["O"]["o_dividends_keyless"]["per"].values())
    src0 = FakeSrc(t)  # a valid reply with zero ex-dates for every probe must FAIL (amendment O4)
    src0.dividends = lambda sym, kind: {"data": {"dividends": {"rows": []}}}
    crit0, detail0 = sm.collect_checks(("O",), {"o_sources": src0}, src0.pm)
    assert crit0["o_dividends_keyless"] is False and all(v["n_dates"] == 0 and not v["ok"] for v in detail0["O"]["o_dividends_keyless"]["per"].values())
    assert crit["o_iv_convention_checked"] is False and detail["O"]["o_iv_convention_checked"]["choice"] == "none"  # too few near-the-money options in the fixture
    assert sm.family_needs("O") == o12.SMOKE_NEEDS
    assert o12.in_smoke_session(t) and not o12.in_smoke_session(o12.et_epoch("2026-10-20", 9, 0)) and not o12.in_smoke_session(o12.et_epoch("2026-10-24", 12, 0))


def test_parser_has_the_o_subcommands_and_declared_arguments(capsys, tmp_path):
    p = run_cb12.build_parser()
    a = p.parse_args(["opt-live"])
    assert a.disk_cap_gb == 0.3 and a.data_dumps_cap_gb == 40.0 and a.rps == 2.0
    assert callable(p.parse_args(["opt-smoke"]).fn) and p.parse_args(["census", "--family", "O"]).family == "O"
    rules = tmp_path / "r.json"
    c12.write_rules(rules)
    code, out = _run(["opt-live", "--rules", rules.as_posix(), "--allow-uncommitted-rules", "--disk-cap-gb", "1.0"], capsys)
    assert code == 2 and "declaration" in out["refused"]
    code, out = _run(["opt-live", "--rules", rules.as_posix(), "--allow-uncommitted-rules", "--freeze-spec", (tmp_path / "none.json").as_posix()], capsys)
    assert code == 2 and "freeze" in out["refused"]
    spec = tmp_path / "cb12_v1.json"
    spec.write_text(json.dumps({"X": {}}))
    code, out = _run(["opt-live", "--rules", rules.as_posix(), "--allow-uncommitted-rules", "--freeze-spec", spec.as_posix()], capsys)
    assert code == 2 and "no 'O' part" in out["refused"]


def test_runner_opt_live_end_to_end_with_fake_sources(capsys, tmp_path, monkeypatch):
    rules = tmp_path / "r.json"
    c12.write_rules(rules)
    spec = tmp_path / "cb12_v1.json"
    spec.write_text(json.dumps({"O": {"frozen_utc": "2026-10-19T12:00:00Z", "iv_convention": "none"}}))
    t = o12.et_epoch("2026-10-20", 11, 0) + 30
    src = FakeSrc(t)
    monkeypatch.setattr(run_cb12, "_o_sources", lambda a: src)
    monkeypatch.setattr(run_cb12.time, "sleep", src.sleep)
    monkeypatch.setattr(run_cb12.time, "time", lambda: src.t)
    base = ["--rules", rules.as_posix(), "--allow-uncommitted-rules", "--standalone", "--freeze-spec", spec.as_posix(), "--history-root", (tmp_path / "history").as_posix(),
            "--data-dumps", tmp_path.as_posix()]
    code, out = _run(["opt-live", *base], capsys)
    assert code == 0 and out["status"] == "checkpoint", out
    assert (tmp_path / "history" / "h12_opt_live" / "raw" / "2026-10-20" / "1100.json.gz").exists()
    src.t = t + 300
    code, out = _run(["opt-live", *base], capsys)
    assert code == 0 and out["status"] == "daily"
    assert json.loads((tmp_path / "history" / "h12_opt_live" / "windows.json").read_text())["w1"]["start"] == "2026-10-20"


def test_opt_smoke_waits_outside_the_session(capsys, tmp_path, monkeypatch):
    rules = tmp_path / "r.json"
    c12.write_rules(rules)
    monkeypatch.setattr(run_cb12.time, "time", lambda: o12.et_epoch("2026-10-24", 12, 0))
    argv = ["opt-smoke", "--rules", rules.as_posix(), "--allow-uncommitted-rules", "--out", (tmp_path / "creative_batch12" / "opt_smoke.json").as_posix()]
    code, out = _run(argv, capsys)
    assert code == 0 and out["status"] == "idle_heartbeat" and "regular US session" in out["idle"]  # first wait: a heartbeat (exit 0, repeat regex unmatched)
    code, out = _run(argv, capsys)
    assert code == 75 and "regular US session" in out["tempfail"]
    assert not (tmp_path / "creative_batch12" / "opt_smoke.json").exists()


def test_o_convention_must_match_the_smoke(tmp_path):
    sp = tmp_path / "opt_smoke.json"
    sp.write_text(json.dumps({"detail": {"O": {"o_iv_convention_checked": {"choice": "act365"}}}, "criteria": {"o_earnings_keyless": True}}))

    class A:
        opt_smoke = str(sp)

    assert run_cb12._o_convention(A, {"iv_convention": "act365"}) == "act365"
    with pytest.raises(c12.Refused):
        run_cb12._o_convention(A, {"iv_convention": "trading_hours"})
    with pytest.raises(c12.Refused):
        run_cb12._o_convention(A, {})
    assert run_cb12._o_earnings_identified(A) is True
