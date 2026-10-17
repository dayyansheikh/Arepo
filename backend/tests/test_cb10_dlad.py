# ruff: noqa: E501
"""CB10-D tests (offline; synthetic fixtures; no network)."""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime

import numpy as np
import pytest

from astrolabe.research_lab import cb10_common as c10
from astrolabe.research_lab import cb10_dlad as dl

# ---- the digital against a numerical call-spread derivative ----------------------------------------------------------------------------------


def _call_linear_smile(S, K, a, b, tau):
    return dl.bs_call(S, K, a + b * math.log(K / S), tau)


@pytest.mark.parametrize("K,a,b", [(100.0, 0.5, 0.0), (104.0, 0.5, -0.4), (96.0, 0.6, 0.3), (110.0, 0.45, -0.8)])
def test_digital_matches_call_spread_derivative(K, a, b):
    S, tau = 100.0, 5 / 365
    sigma = a + b * math.log(K / S)
    h = 1e-3
    num = -(_call_linear_smile(S, K + h, a, b, tau) - _call_linear_smile(S, K - h, a, b, tau)) / (2 * h)
    assert abs(dl.digital(S, K, sigma, tau, b) - min(max(num, 0.001), 0.999)) < 1e-4


def test_digital_clip_and_invalid():
    assert dl.digital(100.0, 1.0, 0.5, 0.01, 0.0) == 0.999
    assert dl.digital(100.0, 1e6, 0.5, 0.01, 0.0) == 0.001
    assert math.isnan(dl.digital(100.0, 100.0, 0.0, 0.01, 0.0))


# ---- Deribit units, per-trade moneyness, flags -----------------------------------------------------------------------------------------------


T0 = datetime(2026, 10, 15, 16, 0, tzinfo=UTC).timestamp()  # 12:00 ET (EDT)


def _trade(ts_off_min, strike, iv, idx=70000.0, amt=1.0, flags=0, exp="17OCT26"):
    return {"ts_ms": int(T0 * 1000 - ts_off_min * 60_000), "instrument": f"BTC-{exp}-{int(strike)}-C", "iv": iv, "index_price": idx, "amount": amt, "flags": flags}


def test_parse_trade_flags_and_percent_units():
    r = dl.parse_trade({"timestamp": 1, "instrument_name": "BTC-17OCT26-70000-C", "iv": 55.0, "index_price": 70000, "amount": 2, "block_trade_id": "b", "liquidation": "T"})
    assert r["flags"] & dl.FLAG_BLOCK and r["flags"] & dl.FLAG_LIQ and not r["flags"] & dl.FLAG_COMBO and r["iv"] == 55.0
    assert dl.parse_trade({"timestamp": 1, "instrument_name": "x", "combo_trade_id": "c"})["flags"] == dl.FLAG_COMBO
    assert dl.parse_trade({"timestamp": 1, "instrument_name": "x", "liquidation": "none"})["flags"] == 0


def test_usable_trades_window_flags_percent_and_own_index():
    rows = [_trade(10, 70000, 50.0, idx=70000.0), _trade(10, 70000, 50.0, idx=71000.0),  # per-trade index
            _trade(121, 70000, 50.0),  # before [t - 120 min]
            _trade(-1, 70000, 50.0),  # after t
            _trade(5, 70000, 50.0, flags=dl.FLAG_BLOCK), _trade(5, 70000, 0.5), _trade(5, 70000, 500.0), _trade(5, 70000, 50.0, idx=0.0)]
    u = dl.usable_trades(rows, T0)
    assert len(u) == 2
    assert u[0]["iv_dec"] == 0.5 and u[0]["m"] == pytest.approx(0.0)
    assert u[1]["m"] == pytest.approx(math.log(70000 / 71000))  # own index_price, not the last trade's
    assert len(dl.usable_trades(rows, T0, include_flagged=True)) == 3
    assert dl.spot_at_origin(rows, T0) == 71000.0  # last REMAINING (unflagged, in-range) trade before t


def test_trade_at_t_is_excluded_causality():
    rows = [{**_trade(0, 70000, 50.0)}]  # timestamp == t: not usable (strictly before t)
    assert dl.usable_trades(rows, T0) == []
    assert math.isnan(dl.spot_at_origin(rows, T0))


def _fit_rows(exp, a, b, n=8, idx=70000.0):
    out = []
    for i in range(n):
        m = -0.1 + 0.2 * i / (n - 1)
        K = idx * math.exp(m)
        out.append({"m": m, "iv_dec": a + b * m, "amount": 1.0 + i, "expiry": exp, "strike": K})
    return out


def test_smile_fit_recovers_line_and_requires_both_sides():
    f = dl.smile_fit(_fit_rows(1.0, 0.55, -0.3))
    assert f["kind"] == "smile" and f["a"] == pytest.approx(0.55) and f["b"] == pytest.approx(-0.3)
    one_side = [x for x in _fit_rows(1.0, 0.55, -0.3, n=12) if x["m"] > 0.01]
    assert dl.smile_fit(one_side)["kind"] != "smile"
    assert dl.smile_fit([])["kind"] is None


def test_atm_fallback_needs_three_trades_and_zero_slope():
    atm = [{"m": 0.01 * i, "iv_dec": 0.5 + 0.01 * i, "amount": 1.0} for i in (-1, 0, 1)]
    f = dl.smile_fit(atm)
    assert f["kind"] == "atm" and f["b"] == 0.0 and f["a"] == pytest.approx(0.5)
    assert dl.smile_fit(atm[:2])["kind"] is None
    far = [{"m": 0.12 + 0.001 * i, "iv_dec": 0.5, "amount": 1.0} for i in range(3)]  # inside 0.15 but outside the ATM band
    assert dl.smile_fit(far)["kind"] is None


# ---- interpolation to T and the 3-day rule ---------------------------------------------------------------------------------------------------


def _exp(day_h):  # epoch of an expiry day_h hours after T0
    return T0 + day_h * 3600


def test_anchor_at_expiry_between_expiries_and_three_day_rule():
    S, K, t = 70000.0, 70000.0, T0
    T = t + 3 * 86400.0
    fit = {"kind": "smile", "a": 0.5, "b": 0.0, "n": 10}
    # one side only (e1 == T): flat sigma from that expiry
    one = dl.anchor_q({T: fit}, S, K, t, T)
    assert one["status"] == "ok" and one["sides"] == 1 and one["sigma"] == pytest.approx(0.5)
    # both sides, equal sigma -> interpolation keeps sigma
    both = dl.anchor_q({T - 86400.0: fit, T + 86400.0: fit}, S, K, t, T)
    assert both["sides"] == 2 and both["sigma"] == pytest.approx(0.5)
    # total variance is linear in time between the two expiries
    f1, f2 = {"kind": "atm", "a": 0.4, "b": 0.0, "n": 3}, {"kind": "atm", "a": 0.6, "b": 0.0, "n": 3}
    e1, e2 = T - 86400.0, T + 86400.0
    r = dl.anchor_q({e1: f1, e2: f2}, S, K, t, T)
    t1, t2, tT = (e1 - t) / dl.YEAR_S, (e2 - t) / dl.YEAR_S, (T - t) / dl.YEAR_S
    w = 0.4**2 * t1 + (0.6**2 * t2 - 0.4**2 * t1) * 0.5
    assert r["sigma"] == pytest.approx(math.sqrt(w / tT))
    # 3-day rule: an expiry more than 3 days from T is not usable
    far = {T + 3 * 86400.0 + 3600.0: fit}
    assert dl.anchor_q(far, S, K, t, T)["status"] == "no_expiry_within_3d"
    assert dl.anchor_q({T + 3 * 86400.0: fit}, S, K, t, T)["status"] == "ok"  # exactly 3 days is inside
    # an expiry at or before t is never used
    assert dl.anchor_q({t - 10.0: fit}, S, K, t, T)["status"] == "no_expiry_within_3d"
    assert dl.anchor_q({T: {"kind": None, "n": 0}}, S, K, t, T)["status"] == "no_expiry_within_3d"


def test_anchor_flat_variant_drops_slope_term():
    T = T0 + 2 * 86400.0
    fit = {T: {"kind": "smile", "a": 0.5, "b": -0.5, "n": 10}}
    q_s = dl.anchor_q(fit, 70000.0, 72000.0, T0, T)["q"]
    q_f = dl.anchor_q(fit, 70000.0, 72000.0, T0, T, flat=True)["q"]
    assert q_f == pytest.approx(dl.digital(70000.0, 72000.0, 0.5, 2 / 365, 0.0)) and q_s != pytest.approx(q_f)


# ---- Polymarket prices: p, p_reg (separate earlier transaction), p_alt, eligibility, labels -------------------------------------------------------


def _tx(*pts):  # (minutes before t, price, size)
    return sorted((T0 - m * 60.0, p, s) for m, p, s in pts)


def test_p_and_p_reg_are_distinct_transactions_five_minutes_apart():
    tx = _tx((100, 0.40, 10), (60, 0.42, 10), (40, 0.45, 10), (20, 0.50, 7), (3, 0.55, 5))
    o = dl.origin_row(tx, T0, oldest_ts=0.0, truncated=False)
    assert o["status"] == dl.ST_ELIGIBLE
    assert o["p"] == 0.55 and o["size_p"] == 5  # last transaction in [t - 30 min, t)
    assert o["p_reg"] == 0.50 and o["t_reg"] != o["t_p"]  # last OTHER transaction before t_p - 5 min
    assert o["t_p"] - o["t_reg"] >= dl.REG_GAP_S
    assert o["p_alt"] == 0.45  # third transaction: before t_reg - 5 min


def test_p_reg_boundary_exactly_five_minutes_excluded_and_window_180():
    tx = _tx((181, 0.30, 1), (180, 0.35, 1), (10, 0.50, 1), (5, 0.60, 1))
    o = dl.origin_row(tx, T0, oldest_ts=0.0, truncated=False)
    assert o["p"] == 0.60
    assert o["p_reg"] == 0.35  # [t - 180 min, ...) is inclusive at the lower end; 181 min is out
    assert o["t_p"] - o["t_reg"] > dl.REG_GAP_S
    tx2 = _tx((180, 0.35, 1), (10, 0.50, 1))  # exactly t_p - 5 min is excluded (upper end exclusive)
    o2 = dl.origin_row(_tx((15, 0.40, 1), (10, 0.50, 1)), T0, oldest_ts=0.0, truncated=False)
    assert o2["p"] == 0.50 and o2["p_reg"] == ""  # 15 min < 10 min + ... t_p - 5 min = 15 min before t: exclusive
    assert dl.origin_row(tx2, T0, oldest_ts=0.0, truncated=False)["p_reg"] == 0.35


def test_freshness_boundaries_t_minus_30_inclusive_t_exclusive():
    o = dl.origin_row(_tx((30, 0.50, 1), (60, 0.40, 1)), T0, oldest_ts=0.0, truncated=False)
    assert o["p"] == 0.50  # t - 30 min is inclusive
    o = dl.origin_row(_tx((30.01, 0.50, 1), (60, 0.40, 1)), T0, oldest_ts=0.0, truncated=False)
    assert o["p"] == ""  # just outside: no fresh transaction
    o = dl.origin_row([(T0, 0.50, 1.0), (T0 - 600, 0.45, 1.0)], T0, oldest_ts=0.0, truncated=False)
    assert o["p"] == 0.45 and o["last_any_price"] == 0.45  # a transaction AT t is not before t


def test_eligibility_uses_last_transaction_of_any_age_and_band_before_freshness():
    old = dl.origin_row(_tx((600, 0.50, 1)), T0, oldest_ts=0.0, truncated=False)
    assert old["status"] == dl.ST_ELIGIBLE and old["p"] == ""  # eligible but later labelled inactive
    band = dl.origin_row(_tx((10, 0.97, 1), (60, 0.5, 1)), T0, oldest_ts=0.0, truncated=False)
    assert band["status"] == dl.ST_BAND
    assert dl.origin_row([], T0, oldest_ts=0.0, truncated=False)["status"] == dl.ST_NEVER
    assert dl.origin_row([], T0, oldest_ts=T0 - 10, truncated=True)["status"] == dl.ST_UNDET  # cap reached, nothing before t


def test_truncation_flag_for_t():
    o = dl.origin_row(_tx((10, 0.5, 1), (20, 0.4, 1)), T0, oldest_ts=T0 - 3600, truncated=True)
    assert o["truncated_for_t"] == 1  # t - 180 min lies before the oldest reachable print
    o = dl.origin_row(_tx((10, 0.5, 1)), T0, oldest_ts=T0 - 4 * 3600, truncated=True)
    assert o["truncated_for_t"] == 0


def test_label_order_truncation_then_deribit_then_inactive():
    base = {"market_id": "1", "asset": "BTC", "d": "2026-10-20", "lag": 5, "t": T0, "strike": 70000.0, "status": dl.ST_ELIGIBLE, "truncated_for_t": 1}
    feat = {"q": 0.5}
    full = {**base, "p": 0.5, "p_reg": 0.4, "p_alt": math.nan}
    assert dl._label_unit(full, "failed", feat)["label"] == dl.LABEL_TRUNC
    assert dl._label_unit({**full, "truncated_for_t": 0}, "failed", feat)["label"] == dl.LABEL_DERIBIT
    assert dl._label_unit({**full, "truncated_for_t": 0}, "ok", {"q": math.nan})["label"] == dl.LABEL_DERIBIT
    assert dl._label_unit({**full, "truncated_for_t": 0, "p_reg": ""}, "ok", feat)["label"] == dl.LABEL_INACTIVE
    assert dl._label_unit({**full, "truncated_for_t": 0}, "ok", feat)["label"] == "available"
    assert dl._label_unit({**full, "status": dl.ST_BAND}, "ok", feat)["label"] is None


# ---- ET clock, Stage-2 cron lines ----------------------------------------------------------------------------------------------------------


def _z(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def test_et_origin_clock_across_2026_11_01():
    assert c10.noon_et("2026-10-31") == _z("2026-10-31T16:00:00Z")  # EDT
    assert c10.noon_et("2026-11-01") == _z("2026-11-01T17:00:00Z")  # DST ended 06:00Z that day
    assert c10.noon_et("2026-11-02") == _z("2026-11-02T17:00:00Z")
    assert [lag for lag, _ in dl.origins_of("2026-11-04")] == [5, 2]
    assert dl.origins_of("2026-11-04")[0][1] == _z("2026-10-30T16:00:00Z") and dl.origins_of("2026-11-04")[1][1] == _z("2026-11-02T17:00:00Z")


@pytest.mark.parametrize("stamp,action", [
    ("2026-10-31T16:00:30Z", "collect"), ("2026-10-31T17:00:30Z", "wrong_line"),
    ("2026-11-01T16:00:30Z", "wrong_line"), ("2026-11-01T17:00:30Z", "collect"),
    ("2026-11-02T16:00:30Z", "wrong_line"), ("2026-11-02T17:00:30Z", "collect"),
    ("2026-10-31T16:20:00Z", "late"), ("2026-10-31T15:59:00Z", "late")])
def test_origin_due_both_cron_minutes_across_dst(stamp, action):
    assert dl.origin_due(_z(stamp))["action"] == action


def test_t10_d2_start_and_dates():
    commit = _z("2026-11-10T12:00:00Z")
    start = dl.t10_d2_start(commit)
    assert c10.noon_et(c10.day_add(start, -5)) >= commit + 86400.0
    assert c10.noon_et(c10.day_add(c10.day_add(start, -1), -5)) < commit + 86400.0
    dates = dl.stage2_dates(start)
    assert len(dates) == dl.STAGE2_DATES == 56 and dates[0] == start
    assert dl.stage2_targets(c10.day_add(start, -5), dates) == [(start, 5)]
    assert dl.stage2_targets("2000-01-01", dates) == []


# ---- series-date rule (+-1 day) --------------------------------------------------------------------------------------------------------------


def _row(mid, ev, d, series="S1", neg=""):
    return {"market_id": mid, "event_id": ev, "event_ids": ev, "d": d, "series_ids": series, "neg_risk_market_id": neg}


def test_series_date_rule_plus_minus_one_day_and_full_series_report():
    frame = [_row("1", "e1", "2026-03-10"), _row("2", "e2", "2026-03-11"), _row("3", "e3", "2026-03-12"), _row("4", "e4", "2026-03-14"), _row("5", "e5", "2026-03-20", "S2")]
    keys = {"event": set(), "neg_risk_market": set(), "series": {"S1"}}
    kept, n = dl.apply_exclusions(frame, set(), keys, {"S1": {"2026-03-11"}})
    ids = {r["market_id"] for r in kept}
    assert ids == {"4", "5"}  # 10, 11, 12 within +-1 day of the excluded 11th; the 14th is not
    assert n["series_date"] == 3 and n["events_dropped"] == 3
    assert n["full_series_rule_events_dropped"] == 4  # the standard series-key rule would have dropped all four S1 events
    kept2, n2 = dl.apply_exclusions(frame, {"4"}, keys, {})
    assert {r["market_id"] for r in kept2} == {"1", "2", "3", "5"} and n2["id"] == 1


def test_thinned_label_over_30_percent():
    frame = [_row(str(i), f"e{i}", "2026-03-10") for i in range(10)]
    keys = {"event": set(), "neg_risk_market": set(), "series": set()}
    _, n = dl.apply_exclusions(frame, {"0", "1", "2", "3"}, keys, {})
    assert n["label"] == "population thinned by exclusions"
    _, n = dl.apply_exclusions(frame, {"0"}, keys, {})
    assert n["label"] is None


# ---- transaction aggregation -----------------------------------------------------------------------------------------------------------------


def test_aggregate_transactions_yes_terms_one_row_per_hash():
    prints = [{"timestamp": 100, "outcomeIndex": 0, "price": 0.40, "size": 10, "transactionHash": "0xa"},
              {"timestamp": 101, "outcomeIndex": 1, "price": 0.58, "size": 10, "transactionHash": "0xa"},
              {"timestamp": 160, "outcomeIndex": 1, "price": 0.30, "size": 5, "transactionHash": "0xb"},
              {"timestamp": 170, "outcomeIndex": 0, "price": 0.50, "size": 0, "transactionHash": "0xc"},  # zero size dropped
              {"timestamp": 180, "outcomeIndex": 0, "price": 1.50, "size": 1, "transactionHash": "0xd"}]  # bad price dropped
    tx = dl.aggregate_transactions(prints, 0)
    assert tx == [(101.0, pytest.approx(0.41), 20.0), (160.0, pytest.approx(0.70), 5.0)]  # outcome-1 prints mapped to 1 - price
    assert all(len(r) == 3 for r in tx)  # no hash is returned
    tx1 = dl.aggregate_transactions(prints[:3], 1)  # NO token index 1 is the YES side's complement
    assert tx1[1][1] == pytest.approx(0.30)
    assert dl.smoke_tx_fixture()["pass"]


# ---- Gamma whitelist and the outcome guard -------------------------------------------------------------------------------------------------


def _live_market(d="2026-10-20", strike=70000, asset="Bitcoin"):
    T = c10.noon_et(d)
    pair = "BTC/USDT" if asset == "Bitcoin" else "ETH/USDT"
    return {"id": "501", "conditionId": "0xc1", "question": f"Will the price of {asset} be above ${strike:,} on October 20?", "slug": "s",
            "clobTokenIds": json.dumps(["tY", "tN"]), "outcomes": json.dumps(["Yes", "No"]),
            "startDate": datetime.fromtimestamp(c10.noon_et(c10.day_add(d, -7)), UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "endDate": datetime.fromtimestamp(T, UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "negRisk": False,
            "description": f"Resolves via the Binance {pair} 1 minute candle at 12:00 ET, the final Close price.",
            "feeSchedule": {"rate": 0.07, "takerOnly": True}, "events": [{"id": "77", "series": [{"id": "9", "slug": "btc-multi-strikes-weekly"}]}],
            # forbidden end-of-life / post-resolution fields
            "outcomePrices": json.dumps(["1", "0"]), "lastTradePrice": 0.99, "bestBid": 0.98, "bestAsk": 1.0, "spread": 0.02, "oneDayPriceChange": 0.4,
            "umaResolutionStatus": "resolved", "umaResolutionStatuses": "[]", "closedTime": "2026-10-20 16:05:00+00", "volume": "123456", "volumeNum": 123456.0,
            "liquidity": "1", "liquidityNum": 1.0, "volume24hr": 5.0}


def test_whitelist_drops_every_forbidden_field_and_routes_outcome_prices_to_guarded_only():
    m = _live_market()
    row, reason, outc = dl.parse_ladder_market(m, "2026-10-20")
    assert reason == "ok" and row is not None
    blob = json.dumps(row)
    for f in c10.GAMMA_FORBIDDEN:
        assert f not in row, f
    assert "0.99" not in blob and "resolved" not in blob and "123456" not in blob and "Binance" not in blob  # description text is not stored
    assert set(row) <= set(dl.FRAME_COLUMNS)
    assert outc["outcome_prices"] == json.dumps(["1", "0"]) and set(outc) == {"market_id", "outcome_labels", "outcome_prices", "d"}
    w = c10.whitelist_market(m, flag_res=dl.flag_res("BTC"))
    c10.assert_whitelisted(w)
    assert w["flag_binance"] == 1 and "description" not in w and w["desc_sha256"]
    with pytest.raises(c10.Refused):
        c10.assert_whitelisted({**w, "lastTradePrice": 1})


def test_frame_rule_reasons():
    d = "2026-10-20"
    assert dl.parse_ladder_market({**_live_market(), "question": "Will BTC hit 80k?"}, d)[1] == "question_re"
    assert dl.parse_ladder_market({**_live_market(), "negRisk": True}, d)[1] == "neg_risk"
    assert dl.parse_ladder_market({**_live_market(), "description": "no flags"}, d)[1].startswith("flags:")
    late = {**_live_market(), "startDate": "2026-10-19T00:00:00Z"}
    assert dl.parse_ladder_market(late, d)[1] == "listed_after_d_minus_5"
    assert dl.parse_ladder_market({**_live_market(), "outcomes": json.dumps(["Up", "Down"])}, d)[1] == "outcomes"
    r = dl.parse_ladder_market(_live_market(strike=1_234_567, asset="Ethereum"), d)[0]
    assert r["asset"] == "ETH" and r["strike"] == 1234567.0
    assert dl.parse_ladder_market({**_live_market(), "endDate": "2026-10-20T10:00:00Z"}, d)[1] == "end_not_noon_et"


def test_guarded_files_open_only_for_screen_and_rep(tmp_path):
    p = tmp_path / "outcomes_guarded.csv.gz"
    with pytest.raises(c10.Refused):
        dl.open_guarded(p, "census")
    with pytest.raises(c10.Refused):
        dl.open_guarded(p, "dlad-frame")
    assert dl.GUARDED_ALLOWED_JOBS == ("screen-D", "rep-D")


def test_outcome_y():
    assert dl.outcome_y(["Yes", "No"], ["1", "0"]) == 1.0
    assert dl.outcome_y(["No", "Yes"], ["1", "0"]) == 0.0
    assert dl.outcome_y(["Yes", "No"], ["0.5", "0.5"]) in (None, 0.5)


# ---- census: no outcome, labels, audit, GD, GDP --------------------------------------------------------------------------------------------


def _synth_units(n_dates=240, sd_gap=0.06, seed=3, beta=1.0, *, alt="noise", start="2026-01-01"):
    rng = np.random.default_rng(seed)
    units = []
    ys = {}
    for i in range(n_dates):
        d = c10.day_add(start, i)
        for asset in dl.ASSETS:
            u_d = rng.random()
            for k in range(4):
                p_reg = float(rng.uniform(0.2, 0.8))
                gap = float(rng.normal(0, sd_gap))
                q = min(max(p_reg + gap, 0.01), 0.99)
                p = min(max(p_reg + float(rng.normal(0, 0.01)), 0.02), 0.98)
                prob = min(max(p + beta * (q - p_reg), 0.0), 1.0)
                y = float(rng.random() < prob)
                mid = f"{asset}{i}{k}"
                p_alt = q - gap + (gap if alt == "q" else float(rng.normal(0, sd_gap)))  # p_alt - p_reg = gap (artefact) or independent noise
                u = {"market_id": mid, "asset": asset, "d": d, "lag": 5, "t": 0.0, "strike": 1.0, "status": dl.ST_ELIGIBLE, "week": c10.iso_week(d), "weekday": "Mon",
                     "month": d[:7], "p": p, "t_p": 0.0, "size_p": 10.0, "p_reg": p_reg, "t_reg": 0.0, "p_alt": p_alt, "p10": p, "p_reg10": p_reg, "q": q, "q_prime": q,
                     "q_rv": p_reg + float(rng.normal(0, 0.03)), "expiry_dist_s": 3600.0, "label": "available", "m_K": 0.0}
                units.append(u)
                ys[mid] = y
        _ = u_d
    return units, ys


def test_census_refuses_outcome_fields_and_reports_labels_and_gates():
    units, _ = _synth_units(n_dates=40)
    with pytest.raises(dl.Refused):
        dl.census_d([{**units[0], "outcome": 1.0}], {})
    for k in ("y", "settle_index", "pnl"):
        with pytest.raises(dl.Refused):
            dl.census_d([{**units[0], k: 1}], {})
    doc = dl.census_d(units, {"status": "fixture"})
    assert doc["labels"] == {"available": len(units)} and doc["coverage_audit"]["pass"] and doc["availability_rule_60"]["pass"]
    assert doc["gate_GD"]["dates"] == 40 and not doc["gate_GD_pass"] and doc["label_D1"] == "not testable (gate GD)" and not doc["d1_runs"]


def test_availability_rule_60_and_coverage_audit_90():
    units, _ = _synth_units(n_dates=40)
    n = len(units)
    deribit_missing = [{**u, "label": dl.LABEL_DERIBIT} for u in units[: int(0.45 * n)]]
    inactive = [{**u, "label": dl.LABEL_INACTIVE} for u in units[int(0.45 * n): int(0.50 * n)]]
    doc = dl.census_d(deribit_missing + inactive + units[int(0.50 * n):], {})
    assert not doc["coverage_audit"]["pass"] and doc["label_D1"] == "not testable (source unavailable)"  # audit < 90% source-available
    assert doc["availability_rule_60"]["pass"] is False and doc["availability_rule_60"]["label"] == "not testable (source unavailable)"
    inact = [{**u, "label": dl.LABEL_INACTIVE} for u in units[: int(0.45 * n)]] + units[int(0.45 * n):]
    doc = dl.census_d(inact, {})
    assert doc["coverage_audit"]["pass"] and doc["availability_rule_60"]["label"] == "not testable (inactivity)"
    assert doc["label_D1"] == "not testable (inactivity)"


def test_gdp_known_answer_pass_and_fail_and_deterministic():
    wide, _ = _synth_units(n_dates=240, sd_gap=0.15)
    a = dl.gdp_mde(wide, draws=60)
    b = dl.gdp_mde(wide, draws=60)
    assert a == b and a["pass"] and 0 < a["mde"] <= dl.GDP["max_mde"] and a["seed"] == 10107 and a["rho"] == 0.8 and a["inflation"] == 1.2
    narrow, _ = _synth_units(n_dates=40, sd_gap=0.004)
    f = dl.gdp_mde(narrow, draws=60)
    assert not f["pass"] and f["mde"] > 1.0
    assert dl.GDP["draws"] == 500 and dl.GDP["z_sum"] == pytest.approx(2.326 + 0.842)
    # hand check of the scaling: MDE = z_sum * 1.2 * SD(beta*)
    assert a["mde"] == pytest.approx(dl.GDP["z_sum"] * 1.2 * a["sd_beta"])


def test_gdp_uses_no_outcome_or_q_beyond_the_feature_gap():
    units, _ = _synth_units(n_dates=60, sd_gap=0.1)
    a = dl.gdp_mde(units, draws=30)
    shifted = [{**u, "size_p": 1.0, "q_prime": 0.0, "q_rv": 0.0} for u in units]  # fields that must not matter
    assert dl.gdp_mde(shifted, draws=30) == a


def test_attribution_not_identifiable_when_cor_above_0_9():
    units, _ = _synth_units(n_dates=60)
    for u in units:
        u["q_rv"] = u["q"] + 1e-4
    doc = dl.census_d(units, {})
    assert doc["features"]["cor_gap_rv"] > 0.9 and doc["features"]["attribution_identifiable"] is False


# ---- D1 statistic: separate regressor, independent-price placebo, labels ---------------------------------------------------------------------


def _y_of(ys):
    return lambda u: ys.get(u["market_id"])


def test_d1_regressor_uses_p_reg_not_p_and_target_uses_p():
    units, ys = _synth_units(n_dates=240)
    res = dl.d1_stat(units, _y_of(ys), n_draws=4)
    y = np.array([ys[u["market_id"]] - u["p"] for u in units])
    x_reg = np.array([u["q"] - u["p_reg"] for u in units])
    x_same = np.array([u["q"] - u["p"] for u in units])
    assert res["beta"] == pytest.approx(c10.ols_slope(y, x_reg))
    assert res["beta"] != pytest.approx(c10.ols_slope(y, x_same))
    assert res["reported"]["same_transaction_slope"] == pytest.approx(c10.ols_slope(y, x_same))  # descriptive only


def test_d1_independent_price_placebo_is_binding():
    clean, ys = _synth_units(n_dates=240, alt="noise")
    res = dl.d1_stat(clean, _y_of(ys), n_draws=4)
    assert res["independent_price_placebo"]["holds"] is True and res["p"] < 0.01 and res["beta"] > dl.D1_FLOOR
    # artefact world: p_alt - p_reg carries the same gap as q - p_reg, so the "alternative" predicts equally -> the credit is withheld
    art, ys2 = _synth_units(n_dates=240, alt="q")
    res2 = dl.d1_stat(art, _y_of(ys2), n_draws=4)
    ind = res2["independent_price_placebo"]
    assert res2["p"] < 0.01 and res2["beta"] > dl.D1_FLOOR
    assert ind["holds"] is False and abs(ind["min_diff"]) < dl.D1_FLOOR
    assert res2["advance"] is False


def test_d1_units_without_p_alt_dropped_from_placebo_only():
    units, ys = _synth_units(n_dates=240)
    for u in units[:100]:
        u["p_alt"] = math.nan
    res = dl.d1_stat(units, _y_of(ys), n_draws=4)
    assert res["n"] == len(units) and res["independent_price_placebo"]["n_dropped"] == 100


def test_d1_no_signal_does_not_advance_and_unresolved_units_counted():
    units, ys = _synth_units(n_dates=240, beta=0.0)
    ys.pop(units[0]["market_id"])
    res = dl.d1_stat(units, _y_of(ys), n_draws=4)
    assert res["n_unresolved"] == 1 and res["advance"] is False
    tiny, _ = _synth_units(n_dates=2)
    assert dl.d1_stat(tiny, lambda u: 1.0, n_draws=2)["verdict"] == "not testable"


def test_d1_attribution_label_when_rv_digital_explains():
    units, ys = _synth_units(n_dates=240, seed=11)
    rng = np.random.default_rng(5)
    for u in units:
        g = u["q"] - u["p_reg"]
        u["q_rv"] = u["p_reg"] + g  # the spot-plus-realised-vol digital carries the whole gap ...
        u["q"] = min(max(u["p_reg"] + g + float(rng.normal(0, 0.06)), 0.01), 0.99)  # ... and the option anchor adds only noise
    res = dl.d1_stat(units, _y_of(ys), n_draws=4, cor_identifiable=True)
    a = res["option_attribution"]
    assert a["joint_beta_q"] < a["solo_beta_q"] / 2 and a["credit_option_implied"] is False
    clean, ys2 = _synth_units(n_dates=240)
    a2 = dl.d1_stat(clean, _y_of(ys2), n_draws=4, cor_identifiable=True)["option_attribution"]
    assert a2["credit_option_implied"] is True and a2["joint_beta_q"] >= a2["solo_beta_q"] / 2
    assert dl.d1_stat(clean, _y_of(ys2), n_draws=4, cor_identifiable=False)["option_attribution"]["credit_option_implied"] is False


# ---- source check, D2 economics and Stage-2 availability -------------------------------------------------------------------------------------


def test_source_check_threshold_two_percent():
    units = [{"market_id": str(i), "asset": "BTC", "d": "2026-01-01", "strike": 100.0} for i in range(100)]
    settle = {("BTC", "2026-01-01"): 110.0}
    ok = dl.source_check(units, settle, lambda u: 1.0)
    assert ok["pass"] and ok["n"] == 100
    bad = dl.source_check(units, settle, lambda u: 0.0 if int(u["market_id"]) < 3 else 1.0)
    assert bad["disagree"] == 3 and bad["pass"] is False
    near = dl.source_check(units, {("BTC", "2026-01-01"): 100.2}, lambda u: 0.0)  # within 0.5%: not scored
    assert near["n"] == 0 and near["pass"] is False


def test_d2_trade_rule_fee_size_and_robustness():
    rate = dl.fee_rate(0.03)
    assert rate == 0.07 and dl.fee_rate(0.10) == 0.10 and dl.fee_rate(math.nan) == 0.07
    books = {"yes": {"best_ask": 0.40, "ask_size": 10.0, "crossed": False}, "no": {"best_ask": 0.65, "ask_size": 10.0, "crossed": False}}
    tr = dl.d2_trade(0.55, books, rate)
    assert tr["token"] == "yes" and tr["edge"] == pytest.approx(0.55 - 0.40 - 0.07 * 0.4 * 0.6)
    assert dl.d2_trade(0.55, {**books, "yes": {**books["yes"], "ask_size": 4.0}}, rate) is None  # size at the ask < 5
    assert dl.d2_trade(0.55, {**books, "yes": {**books["yes"], "crossed": True}}, rate) is None
    assert dl.d2_trade(0.43, books, rate) is None  # edge below 4c
    assert dl.d2_trade(0.55, books, rate, cost_add=0.005)["a"] == pytest.approx(0.405)
    assert dl.clob_book_state({"bids": [{"price": "0.6", "size": "1"}], "asks": [{"price": "0.5", "size": "2"}]})["crossed"] is True


def test_stage2_availability_20_percent_rule():
    days = [f"d{i}" for i in range(10)]
    ok = dl.stage2_availability({d: "ok" for d in days[:8]} | {days[8]: "unavailable (host disk)"}, days)  # one more missing -> scheduling
    assert ok["unavailable_share"] == pytest.approx(0.2) and ok["testable"]
    bad = dl.stage2_availability({d: "ok" for d in days[:7]} | {days[7]: "unavailable (source)", days[8]: "unavailable (source)"}, days)
    assert not bad["testable"] and bad["label"] == "not testable (unavailable (source))"


def test_haircut_uses_only_supplied_deribit_samples():
    h = dl.haircut_h([(0.4, 0.5), (0.45, 0.5), (math.nan, 0.5), (0.5, 0.0)])
    assert h["n"] == 2 and h["h"] == pytest.approx(1 - np.median([0.8, 0.9]))
    assert dl.HAIRCUT_WINDOW == ("2025-07-01", "2025-10-01")


def test_rv_sigma_causal_bars_only():
    t = T0
    bars = [(int(T0 * 1000 - (i + 1) * 3_600_000), 100.0, 100.0 * (1 + 0.001 * ((-1) ** i))) for i in range(167, -1, -1)]
    s = dl.rv_sigma(bars, t)
    assert math.isfinite(s) and s > 0
    # a bar whose hour is not complete at t (open within the last hour) is never used
    partial = bars + [(int(T0 * 1000 - 1_800_000), 100.0, 1e6)]
    assert dl.rv_sigma(partial, t) == s
    assert math.isnan(dl.rv_sigma(bars[:100], t))  # fewer than 150 returns
