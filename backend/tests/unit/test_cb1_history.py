# ruff: noqa: E501
"""CB1 history tests A / C / E: causality, target construction, trial counting, fail-closed guards, determinism.
Synthetic fixtures only (no network, no real data)."""

from __future__ import annotations

import gzip
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import battery2, economics, h5_seal
from astrolabe.research_lab import cb1_history as cb

END = 236_112 * 7200 + 1800  # not on the 2h grid: the first grid point at/after it is END + 5400
DAY = 86400.0


# ----------------------------------------------------------------------------------------------- fixtures
def iso(ts: float) -> str:
    from datetime import UTC, datetime

    return datetime.fromtimestamp(ts, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _gz(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(text.encode(), mtime=0))


def price_series(start: float, stop: float, p: float, overrides: dict[float, float] | None = None, step: float = 600.0):
    out = []
    t = start
    while t <= stop:
        out.append((t, (overrides or {}).get(t, p)))
        t += step
    return out


def write_run(root: Path, name: str, markets: list[dict], t_fetch: float, sample_extra: bool = True) -> Path:
    run = root / name
    run.mkdir(parents=True, exist_ok=True)
    (run / "manifest.json").write_text(json.dumps({"run_id": name, "request_clock_now": iso(t_fetch), "lookback_days": 450}))
    rows, prog = [], []
    for m in markets:
        mid = m["id"]
        rows.append({
            "market_id": mid, "event_id": m.get("event", f"ev{mid}"), "fee_category": m.get("cat", "politics"),
            "status": "closed" if m.get("closed", 1) else "active", "created_at": iso(m["created"]),
            "end_at": iso(m["end"]), "closed_time": iso(m["close"]) if m.get("close") else "",
            "closed": m.get("closed", 1), "uma_status": "resolved", "outcome_prices": m.get("outcome_prices", '["1","0"]'),
            "start_epoch": m["created"], "end_epoch": m["end"], "close_epoch": m.get("close", ""), "liquidity": 1.0, "volume": 1.0,
            "stratum": "s", "question": m.get("question", "Will it happen?"), "outcomes": m.get("outcomes", '["Yes", "No"]'),
        })
        prog.append({"market_id": mid, "status": "done", "trades_truncated": m.get("truncated", False),
                     "trades_oldest_ts": m.get("oldest")})
        _gz(run / "prices" / f"{mid}.csv.gz", "t,p\n" + "".join(f"{t},{p}\n" for t, p in m["prices"]))
        _gz(run / "trades" / f"{mid}.csv.gz", "ts,side,size,price,outcome_index,wallet_hash,trade_key\n" + "".join(
            f"{ts},{side},{size},{price},{oi},w,{mid}-{i}\n" for i, (ts, side, size, price, oi) in enumerate(m["trades"])))
    _gz(run / "sample.csv.gz", pd.DataFrame(rows).to_csv(index=False))
    (run / "progress.jsonl").write_text("".join(json.dumps(p) + "\n" for p in prog))
    return run


def a1_market(mid="m1", p=0.97, trades=None, close=None, closed=1, overrides=None, **kw):
    created = END - 10 * DAY
    return {"id": mid, "created": created, "end": END, "close": END + 2 * DAY if close is None else close, "closed": closed,
            "prices": price_series(created, END + 2 * DAY, p, overrides),
            "trades": trades if trades is not None else [(END - 3600, "BUY", 5, p, 0), (END + 1800, "BUY", 5, p, 0)], **kw}


def ctx_for(t_fetch=END + 300 * DAY) -> cb.Ctx:
    return cb.Ctx(run_id="h2_main", t_fetch=t_fetch, t_censor=t_fetch)


def one_market(rec_market: dict, fn, ctx: cb.Ctx | None = None):
    """Run a selector on one written-and-read market (the real loading path)."""
    import tempfile

    ctx = ctx or ctx_for()
    with tempfile.TemporaryDirectory() as td:
        run = write_run(Path(td), "h2_main", [rec_market], ctx.t_fetch)
        frame = cb.load_sample(run)
        (rec, ts, vals, tr, trunc, oldest), = list(cb.iter_markets(run, frame))
        tr_ts = np.sort(tr["ts"].to_numpy(float)) if len(tr) else np.empty(0)
        return fn(rec, ts, vals, tr_ts, trunc, oldest, ctx), rec, ts, vals


def long_units(n=600, lose=(), p=0.97, d=30.0, test="A1", cat="politics", month_weeks=20) -> pd.DataFrame:
    a = p + cb.half_spread(p)
    f = cb.taker_fee_ps(a, cb.fee_rate(cat))
    rows = []
    for i in range(n):
        rows.append(dict(test=test, market_id=str(i), event=f"e{i}", category=cat, t=1.7e9 + i * 3600.0, side=0, p_side=p, a=a, f=f,
                         close_epoch=1.7e9 + 40 * DAY, end_epoch=1.7e9, closed=1, psu=f"p|{i % 7}", w=1.0, kind="long",
                         Y=0.0 if i in set(lose) else 1.0, status="resolved", censored=False, d=d,
                         week=f"2026-W{(i % month_weeks) + 1:02d}", market="x"))
    return cb.finalize_net(pd.DataFrame(rows).drop(columns=["market"]))


# ----------------------------------------------------------------------------------------------- cost model
def test_cost_tables_and_fees_match_economics():
    assert cb.half_spread(0.03) == 0.0205 and cb.half_spread(0.10) == 0.015 and cb.half_spread(0.5) == 0.011
    assert cb.half_spread(0.9) == 0.015 and cb.half_spread(0.97) == 0.0125 and cb.half_spread(1.0) == 0.0125
    assert cb.fee_rate("sports") == 0.05 and cb.fee_rate("crypto") == 0.07 and cb.fee_rate(None) == 0.07
    assert cb.fee_rate("politics") == 0.04 and cb.fee_rate("geopolitics") == 0.0 and cb.fee_rate("weird") == 0.07
    assert cb.taker_fee_ps(0.5, 0.05) == pytest.approx(economics.taker_fee(1.0, 0.5, 0.05))
    c = cb.cost_model(0.97, "politics")
    assert c.ask == pytest.approx(0.9825) and c.capital == pytest.approx(c.ask + c.fee)
    assert cb.cost_model(0.99, "politics").ask == pytest.approx(0.999 if 0.99 + 0.0125 > 0.999 else 1)  # capped
    assert cb.cost_model(0.60, "politics", genesis=True).ask == pytest.approx(0.625)  # genesis half-spread floor 2.5c
    assert cb.cost_model(0.97, "politics", extra=cb.COST_SENS).ask == pytest.approx(0.99)


def test_r_ann_arithmetic():
    df = pd.DataFrame({"net": [0.02, 0.02], "K": [1.0, 1.0], "d": [10.0, 30.0]})
    assert cb.r_ann(df) == pytest.approx(365 * 0.04 / 40.0)
    assert cb.r_ann(pd.DataFrame({"net": [0.02], "K": [1.0], "d": [0.2]})) == pytest.approx(365 * 0.02)  # hold floor of 1 day


def test_parse_outcome0():
    assert cb.parse_outcome0('["1","0"]') == 1.0 and cb.parse_outcome0('["0","1"]') == 0.0
    assert cb.parse_outcome0('["0.5","0.5"]') == 0.5
    for bad in (None, "", "garbage", '["0.3","0.7"]', float("nan"), '["1"]'):
        assert cb.parse_outcome0(bad) is None


# ----------------------------------------------------------------------------------------------- truncation rule
def test_trade_condition_known_true_unavailable_never_zero():
    ts = np.array([100.0, 200.0, 300.0])
    # untruncated: plain count
    assert cb.trade_condition_state(ts, False, None, 150.0, 250.0, 1).tolist() == [1]
    assert cb.trade_condition_state(ts, False, None, 400.0, 500.0, 1).tolist() == [0]
    # truncated, window starting before the oldest stored trade: True if satisfied, else unavailable (not 0)
    assert cb.trade_condition_state(ts, True, 100.0, -np.inf, 250.0, 1).tolist() == [1]
    assert cb.trade_condition_state(ts, True, 100.0, -np.inf, 50.0, 1).tolist() == [-1]
    assert cb.trade_condition_state(ts, True, 100.0, 100.0, 150.0, 2).tolist() == [0]  # window starts at the oldest: known
    assert cb.trade_condition_state(ts, True, None, 10.0, 20.0, 1).tolist() == [-1]  # no oldest recorded: nothing known
    assert cb.trade_condition_state(ts, True, float("nan"), 10.0, 20.0, 1).tolist() == [-1]
    # a trade at exactly t does not count (venue ts < t)
    assert cb.trade_condition_state(ts, False, None, 0.0, 200.0, 2).tolist() == [0]


def test_unavailable_earlier_candidate_excludes_market():
    ok = np.array([True, True, True])
    assert cb.first_qualifying(ok, np.array([-1, 1, 1])) == (0, "unavailable")
    assert cb.first_qualifying(ok, np.array([0, 1, 1])) == (1, "selected")
    assert cb.first_qualifying(np.array([False, True, True]), np.array([-1, 1, 1])) == (1, "selected")  # non-trade failures never count
    assert cb.first_qualifying(ok, np.array([0, 0, 0])) == (-1, "none")


# ----------------------------------------------------------------------------------------------- A: origins and causality
def test_a1_first_grid_origin_after_end_and_causal():
    (u, ex), rec, ts, vals = one_market(a1_market(), cb.select_a1)
    t_expect = END + 5400
    assert ex is None and u["t"] == t_expect and u["t"] % 7200 == 0
    assert u["side"] == 0 and u["p_side"] == pytest.approx(0.97) and u["a"] == pytest.approx(0.9825)
    # a planted post-t price spike does not move the selected origin or its price
    spike = {t_expect + 3 * 3600.0: 0.5, t_expect + 7200.0: 0.2}
    (u2, _), *_ = one_market(a1_market(overrides=spike), cb.select_a1)
    assert u2["t"] == u["t"] and u2["p_side"] == u["p_side"]
    # changing closed_time (after t) changes nothing; a close before t removes the market via "open at t"
    (u3, _), *_ = one_market(a1_market(close=END + 30 * DAY), cb.select_a1)
    assert u3["t"] == u["t"]
    (u4, ex4), *_ = one_market(a1_market(close=END + 3600.0), cb.select_a1)
    assert u4 is None and ex4 is None
    # price points are usable only from stamp + 600 s: a stamp at t - 300 s must not be used
    p = price_series(END - 10 * DAY, END + 2 * DAY, 0.97, {})
    p = [(t, (0.5 if t == t_expect - 600 else v)) for t, v in p]
    m = a1_market()
    m["prices"] = p
    (u5, _), *_ = one_market(m, cb.select_a1)
    assert u5["t"] == t_expect and u5["p_side"] == pytest.approx(0.97)  # the stamp at t - 600 s is not yet known at t


def test_a1_requires_trades_and_excludes_sports_and_band():
    # no trade in [end_at, t): not qualifying at the first origin; the later grid origin qualifies if a trade arrives
    m = a1_market(trades=[(END - 3600, "BUY", 5, 0.97, 0)])
    (u, ex), *_ = one_market(m, cb.select_a1)
    assert u is None and ex is None
    m = a1_market(trades=[(END - 3600, "BUY", 5, 0.97, 0), (END + 5400 + 100, "BUY", 5, 0.97, 0)])
    (u, _), *_ = one_market(m, cb.select_a1)
    assert u["t"] == END + 5400 + 7200
    # sports excluded from the A1 primary; price outside 0.95-0.99 excluded
    (u, ex), *_ = one_market(a1_market(cat="sports"), cb.select_a1)
    assert u is None and ex is None
    (u, _), *_ = one_market(a1_market(p=0.80), cb.select_a1)
    assert u is None
    # the favourite side is token 1 when p0 < 0.5
    (u, _), *_ = one_market(a1_market(p=0.03), cb.select_a1)
    assert u["side"] == 1 and u["p_side"] == pytest.approx(0.97)


def test_a1_truncated_market_is_excluded_not_zero():
    # truncated: nothing known before the oldest stored trade, so "a trade before end_at" is unavailable
    m = a1_market(trades=[(END + 1800, "BUY", 5, 0.97, 0)], truncated=True, oldest=END + 1800)
    (u, ex), *_ = one_market(m, cb.select_a1)
    assert u is None and ex is not None and ex["reason"] == "trade_truncation_unavailable"
    # the same market, untruncated, simply fails the condition (not an exclusion)
    m = a1_market(trades=[(END + 1800, "BUY", 5, 0.97, 0)])
    (u, ex), *_ = one_market(m, cb.select_a1)
    assert u is None and ex is None


def test_a2_scheduled_life_and_pre_end_window():
    created = END - 50 * DAY
    m = {"id": "x", "created": created, "end": END, "close": END + 5 * DAY, "closed": 1,
         "prices": price_series(created, END + DAY, 0.97), "trades": [(created + 40 * DAY, "BUY", 5, 0.97, 0)]}
    (u, ex), *_ = one_market(m, cb.select_a2)
    assert ex is None and u["t"] < END - 24 * 3600 and u["t"] % 7200 == 0
    # the 7d look-back needs a trade: the first origin with a trade in [t-7d, t) is chosen
    assert u["t"] > created + 40 * DAY
    # scheduled life > 100 days: not in A2
    m2 = {**m, "created": END - 120 * DAY, "prices": price_series(END - 120 * DAY, END + DAY, 0.97)}
    (u2, _), *_ = one_market(m2, cb.select_a2)
    assert u2 is None
    # end_at beyond T_fetch + 400d: not in A2
    (u3, _), *_ = one_market(m, cb.select_a2, ctx_for(END - 500 * DAY))
    assert u3 is None


def test_origin_horizon_t_le_censor_minus_60d():
    (u, _), *_ = one_market(a1_market(), cb.select_a1, ctx_for(END + 30 * DAY))
    assert u is None


# ----------------------------------------------------------------------------------------------- targets
def base_unit(**kw):
    u = {"test": "A1", "market_id": "m", "event": "e", "category": "politics", "t": 1000.0, "side": 0, "p_side": 0.97, "a": 0.9825,
         "f": cb.taker_fee_ps(0.9825, 0.04), "close_epoch": 5000.0 + 3 * DAY, "end_epoch": 900.0, "closed": 1, "psu": "p", "w": 1.0, "kind": "long"}
    u.update(kw)
    return u


def test_attach_outcome_resolved_5050_missing_and_mirror():
    ctx = cb.Ctx("h2_main", 1e10, 1e10)
    ts, vals = np.array([0.0]), np.array([0.97])
    u = cb.attach_outcome(base_unit(), 1.0, ts, vals, ctx)
    assert u["Y"] == 1.0 and u["status"] == "resolved" and u["d"] == pytest.approx(3.0 + 4000 / DAY, rel=1e-6)
    u = cb.attach_outcome(base_unit(side=1), 1.0, ts, vals, ctx)  # token 1 held, token 0 pays -> loses
    assert u["Y"] == 0.0
    assert cb.attach_outcome(base_unit(), 0.5, ts, vals, ctx)["status"] == "5050"
    assert cb.attach_outcome(base_unit(), None, ts, vals, ctx)["status"] == "missing"
    assert cb.attach_outcome(base_unit(close_epoch=float("nan")), 1.0, ts, vals, ctx)["status"] == "missing"
    assert cb.finalize_net(pd.DataFrame([cb.attach_outcome(base_unit(), 1.0, ts, vals, ctx)]))["net"].iloc[0] == pytest.approx(
        1 - 0.9825 - cb.taker_fee_ps(0.9825, 0.04))


def test_censored_position_marked_at_last_price_minus_costs():
    ctx = cb.Ctx("h2_main", 1e9, 1e9)
    ts, vals = np.array([0.0, 600.0]), np.array([0.5, 0.96])
    u = cb.attach_outcome(base_unit(closed=0, close_epoch=float("nan")), None, ts, vals, ctx)
    assert u["censored"] and u["status"] == "censored"
    exp = 0.96 - cb.half_spread(0.96) - cb.taker_fee_ps(0.96, 0.04)
    assert u["Y"] == pytest.approx(exp)
    s = cb.attach_outcome(base_unit(kind="short", a=0.06, f=0.0, side=0, closed=0, close_epoch=float("nan")), None, ts, np.array([0.5, 0.05]), ctx)
    assert s["Y"] == pytest.approx(0.05 + cb.half_spread(0.05))  # short cheap side: bought back at last + h
    assert cb.finalize_net(pd.DataFrame([s]))["K"].iloc[0] == pytest.approx(1 - 0.06)


def test_e_genesis_origin_pricing_and_targets():
    cre = END - 40 * DAY
    t = cre + 86400
    m = {"id": "g", "created": cre, "end": cre + 30 * DAY, "close": cre + 4 * DAY, "closed": 1, "outcome_prices": '["0","1"]',
         "prices": price_series(cre, cre + 31 * DAY, 0.40, {t + 7 * DAY - 1200: 0.30}),
         "trades": [(cre + 100, "BUY", 5, 0.4, 0), (cre + 200, "SELL", 5, 0.4, 0), (cre + 300, "BUY", 5, 0.4, 0)]}
    (u, ex), rec, ts, vals = one_market(m, cb.select_e)
    assert ex is None and u["t"] == t and u["side"] == 1 and u["p_yes"] == pytest.approx(0.40)
    assert u["a"] == pytest.approx(0.60 + max(cb.half_spread(0.60), cb.GENESIS_H_MIN))  # 2.5c floor
    ctx = ctx_for()
    out = cb.attach_outcome({**u, "t_hold": u["t"]}, 0.0, ts, vals, ctx)
    assert out["Y"] == 1.0  # NO pays when YES resolves 0
    # market closed before t + 7d: drift is payout - p_yes
    assert cb.e_drift(out, rec, ts, vals, 0.0) == pytest.approx(0.0 - 0.40)
    # market still open at t + 7d: drift is the as-of price (stamp + 600 s < t + 7d) minus p_yes
    assert cb.e_drift({**out, "close_epoch": cre + 20 * DAY}, rec, ts, vals, 0.0) == pytest.approx(0.30 - 0.40)
    # only 2 trades before t -> not enough; a trade at t + 1 s must not count
    m2 = {**m, "trades": m["trades"][:2] + [(t + 1, "BUY", 5, 0.4, 0)]}
    (u2, ex2), *_ = one_market(m2, cb.select_e)
    assert u2 is None and ex2 is None
    # a truncated market whose stored trades start after created_at, with < 3 stored: unavailable -> excluded
    m3 = {**m, "trades": m["trades"][:2], "truncated": True, "oldest": cre + 100}
    (u3, ex3), *_ = one_market(m3, cb.select_e)
    assert u3 is None and ex3["reason"] == "trade_truncation_unavailable"
    # scheduled life uses end_at and created_at only: 120 days -> excluded whatever the close
    m4 = {**m, "end": cre + 120 * DAY, "close": cre + 2 * DAY}
    assert one_market(m4, cb.select_e)[0] == (None, None)
    # sports and non-Yes/No labels are excluded
    assert one_market({**m, "cat": "sports"}, cb.select_e)[0] == (None, None)
    assert one_market({**m, "outcomes": '["Over", "Under"]'}, cb.select_e)[0] == (None, None)
    # YES price outside [0.05, 0.80]
    m5 = {**m, "prices": price_series(cre, cre + 31 * DAY, 0.90)}
    assert one_market(m5, cb.select_e)[0] == (None, None)


def test_sensational_frozen_rule_fixtures():
    assert cb.sensational("Will Donald Trump be arrested in 2026?")
    assert cb.sensational("Will the country sanction Vladimir Putin this year?")
    assert not cb.sensational("Trump arrested?")  # sentence-start capital run is not preceded by a lowercase letter
    assert not cb.sensational("Supreme Court bans the measure")  # same exclusion
    assert not cb.sensational("Will bitcoin crash in June?")  # no name
    assert not cb.sensational("Will Donald Trump visit Paris?")  # name but no verb
    assert not cb.sensational(None)
    assert len(cb.e3_text_rule_sha256()) == 64


# ----------------------------------------------------------------------------------------------- C: queue rule
def trades_df(rows):
    return pd.DataFrame(rows, columns=["ts", "side", "size", "price", "outcome_index"])


def test_queue_fill_needs_q0_plus_five_at_or_above_ask():
    t, a_c = 1000.0, 0.06
    tr = trades_df([(t + 10, "BUY", 8, 0.06, 0), (t + 20, "BUY", 100, 0.05, 0), (t + 30, "SELL", 4, 0.94, 1), (t + 40, "BUY", 3, 0.07, 0)])
    arr = cb.buys_longshot(tr, 0)
    r = cb.queue_fill(arr, t, a_c, 10.0)  # need 15: 8 + 4 (sell of the other token at 0.94 = buy at 0.06) + 3 = 15
    assert r["filled"] and r["t_fill"] == t + 40 and r["touch"] and r["through"]
    assert not cb.queue_fill(arr, t, a_c, 11.0)["filled"]  # a print below the ask never fills
    # prints only below the ask: touch false, no fill
    low = cb.buys_longshot(trades_df([(t + 5, "BUY", 500, 0.05, 0)]), 0)
    lr = cb.queue_fill(low, t, a_c, 0.0)
    assert not lr["filled"] and not lr["touch"] and not lr["through"]
    # order life is [t, t + 6h): a trade at t + 6h is outside; one at t is not after the order
    edge = cb.buys_longshot(trades_df([(t, "BUY", 500, 0.06, 0), (t + 6 * 3600, "BUY", 500, 0.06, 0)]), 0)
    assert not cb.queue_fill(edge, t, a_c, 0.0)["filled"]


def test_longshot_orders_token1_mirror_truncation_and_bounds():
    rec = cb.norm_rec({"market_id": "c1", "event_id": "e", "fee_category": "politics", "closed": 1, "created_at": iso(END - 30 * DAY),
                       "start_epoch": END - 30 * DAY, "end_epoch": END, "close_epoch": END + DAY})
    t0 = END - 5 * DAY
    books = pd.DataFrame([{"market_id": "c1", "origin_ts": t0, "state": "two_sided", "sw_best_bid": 0.92, "sw_best_ask": 0.94,
                           "sw_bid_size_1": 20.0, "sw_ask_size_1": 50.0}])
    # token 1 is the longshot (mid0 = 0.93 -> m_c = 0.07): ask = 1 - best_bid0 = 0.08, queue = bid size of token 0
    tr = trades_df([(t0 - DAY, "BUY", 1, 0.9, 0), (t0 + 60, "SELL", 25, 0.92, 0)])  # sell token0 at 0.92 = buy token1 at 0.08
    ts_p, vals_p = np.array([t0 - 2 * DAY, t0, t0 + DAY - 3600, t0 + DAY + 3600]), np.array([0.9, 0.93, 0.95, 0.5])
    ctx = ctx_for()
    od, ex = cb.longshot_orders(books, rec, tr, False, None, ts_p, vals_p, ctx)
    assert not ex and len(od) == 1
    o = od[0]
    assert o["side"] == 1 and o["a_c"] == pytest.approx(0.08) and o["Q0"] == 20.0 and o["m_c"] == pytest.approx(0.07)
    assert o["filled"] and o["t_fill"] == t0 + 60 and o["kind"] == "short" and o["f"] == 0.0
    # post-fill drift uses only the t_fill + 24h point: as-of point at t_fill + 24h is the 0.95 (token-1 mid 0.05)
    assert o["drift24"] == pytest.approx(0.05 - 0.07)
    # truncated market whose oldest stored trade is after the order start: excluded, and enters the bound as a filled loser
    od2, ex2 = cb.longshot_orders(books, rec, tr, True, t0 + 10, ts_p, vals_p, ctx)
    assert not od2 and ex2[0]["reason"] in ("trade_truncation_unavailable", "life_before_oldest_trade")
    f = cb.finalize_net(pd.DataFrame([{**o, "Y": 0.0, "status": "resolved", "censored": False, "d": 5.0, "week": "w"}]))
    tb = cb.truncation_bound(f, [{**ex2[0], "y_tag": "lose"}], "C1")
    assert tb["n_excluded"] == 1 and tb["by_outcome"] == {"lose": 1}
    assert tb["mean_with_excluded_as_losers"] == pytest.approx((0.08 + (0.08 - 1.0)) / 2)  # short loser: a_c - 1
    # a longshot outside [0.02, 0.10] makes no order
    books2 = books.assign(sw_best_bid=0.60, sw_best_ask=0.62)
    assert cb.longshot_orders(books2, rec, tr, False, None, ts_p, vals_p, ctx) == ([], [])


def test_px1_bound_requires_upper_bound_below_captured_spread():
    rng = np.random.default_rng(1)
    nf, nu = 300, 600
    ev_f, ev_u = rng.integers(0, 150, nf).astype(str), rng.integers(0, 150, nu).astype(str)
    wk_f, wk_u = rng.integers(0, 10, nf).astype(str), rng.integers(0, 10, nu).astype(str)
    clean = cb.px1_bound(rng.normal(0, 0.002, nf), rng.normal(0, 0.002, nu), ev_f, ev_u, wk_f, wk_u, 0.01, 2, n_boot=200)
    assert clean["testable"] and clean["clean"] and clean["upper_bound"] < 0.01
    dirty = cb.px1_bound(rng.normal(0.02, 0.002, nf), rng.normal(0, 0.002, nu), ev_f, ev_u, wk_f, wk_u, 0.01, 2, n_boot=200)
    assert not dirty["clean"]
    assert not cb.px1_bound(np.array([0.0]), rng.normal(0, 0.002, nu), ev_f[:1], ev_u, wk_f[:1], wk_u, 0.01, 1)["testable"]


# ----------------------------------------------------------------------------------------------- statistics
def test_clopper_pearson_and_tail_bound_methods():
    assert cb.clopper_pearson(0, 100, 0.99, "upper") == pytest.approx(1 - 0.01 ** (1 / 100))
    assert cb.clopper_pearson(5, 50, 0.95, "upper") == pytest.approx(0.2007, abs=2e-3)  # scipy reference
    assert cb.clopper_pearson(0, 10, 0.95, "lower") == 0.0
    losses = np.zeros(300, bool)
    losses[:3] = True
    tb = cb.tail_bound(losses, np.array([f"e{i}" for i in range(300)]), 0.01)
    assert tb["method"] == "clopper_pearson_event_level" and tb["losing_clusters"] == 3 and not tb["z_usable"]
    # >= 10 losing clusters: Wilson on n / deff
    losses[:20] = True
    tb2 = cb.tail_bound(losses, np.array([f"e{i}" for i in range(300)]), 0.05)
    assert tb2["method"] == "wilson_n_over_deff" and tb2["z_usable"] and tb2["bound"] > 20 / 300
    # clustering: losses concentrated in 3 events give deff > 1 and a looser bound than iid
    ev = np.repeat([f"e{i}" for i in range(60)], 5)
    cl = np.zeros(300, bool)
    for k in range(12):  # 12 losing events, each fully losing
        cl[k * 5 : k * 5 + 5] = True
    tb3 = cb.tail_bound(cl, ev, 0.05)
    assert tb3["deff"] > 1.5 and tb3["bound"] > cb.wilson_bound(cl.mean(), 300, 0.95, "upper")


def test_holm():
    h = cb.holm({"a": 0.001, "b": 0.02, "c": 0.04})
    assert h["a"]["reject"] and h["a"]["p_holm"] == pytest.approx(0.003)
    assert h["b"]["reject"] and h["b"]["p_holm"] == pytest.approx(0.04) and h["c"]["p_holm"] == pytest.approx(0.04)
    h2 = cb.holm({"a": 0.03, "b": 0.04})
    assert not h2["a"]["reject"] and not h2["b"]["reject"]


def test_gate_advances_clean_carry_and_blocks_fat_tail(tmp_path):
    good = cb.evaluate_test(long_units(), "A1", n_boot=100, n_placebo=20)
    assert good["testable"] and good["tail"]["ok"] and good["floor_ok"] and good["rann_ok"]
    assert good["robustness"]["ok"] and good["placebo"]["ok"] and good["advance"]
    # 4% of events lose: above break-even (~1.7%): the tail gate blocks, regardless of any p-value
    bad = cb.evaluate_test(long_units(lose=range(0, 600, 25)), "A1", n_boot=100, n_placebo=10)
    assert not bad["advance"] and "tail_gate" in bad["fail"]
    # fewer than 30 event clusters / 100 units: not testable (p = 1)
    small = cb.evaluate_test(long_units(n=50), "A1", n_boot=50, n_placebo=5)
    assert small["testable"] is False and small["p"] == 1.0 and not small["advance"]
    empty = cb.evaluate_test(pd.DataFrame(), "A1", n_boot=50, n_placebo=5)
    assert empty["testable"] is False and not empty["advance"]


def test_breakeven_placebo_rarely_advances_and_is_deterministic():
    df = long_units(n=800)
    spec = cb.HYPOTHESES_CB1["A1"]
    p1 = cb.breakeven_placebo(df, spec, cb.ALPHA_STAGE1, n_draws=60)
    p2 = cb.breakeven_placebo(df, spec, cb.ALPHA_STAGE1, n_draws=60)
    assert p1 == p2 and p1["advance_rate"] <= cb.PLACEBO_MAX_RATE and p1["ok"]
    # the expected net at the placebo probability is exactly zero
    pb = cb.breakeven_prob(df)
    assert np.allclose(pb * 1.0 - (df["a"] + df["f"]), 0.0)
    short = pd.DataFrame({"kind": ["short"], "a": [0.07], "f": [0.0]})
    assert cb.breakeven_prob(short)[0] == pytest.approx(0.07)


def test_evaluate_is_deterministic():
    a = cb.evaluate_test(long_units(lose=[3, 400]), "A1", n_boot=100, n_placebo=10)
    b = cb.evaluate_test(long_units(lose=[3, 400]), "A1", n_boot=100, n_placebo=10)
    assert json.dumps(a, sort_keys=True, default=cb._jsonable) == json.dumps(b, sort_keys=True, default=cb._jsonable)


def test_e2_mechanism_sign_is_negative():
    df = long_units(n=300, test="E1")
    df["drift"] = -0.02
    df.loc[df.index % 3 == 0, "drift"] = -0.011  # variation so the CR1 SE is non-zero
    r = cb.evaluate_test(df, "E2", n_boot=100)
    assert r["sign_tested"] == -1 and r["floor_ok"] and r["p_ok"] and r["mean"] < -0.005
    df["drift"] = +0.02
    assert not cb.evaluate_test(df, "E2", n_boot=100)["floor_ok"]


# ----------------------------------------------------------------------------------------------- end-to-end build on a synthetic run
def build_run(tmp_path: Path, n=12) -> tuple[Path, cb.Ctx]:
    ms = []
    for i in range(n):
        ms.append(a1_market(f"m{i}", close=END + (2 + i) * DAY))
    run = write_run(tmp_path, "h2_main", ms, END + 300 * DAY)
    return run, ctx_for()


def test_build_family_units_a_and_determinism(tmp_path):
    run, ctx = build_run(tmp_path)
    r1 = cb.build_family_units(run, "A", ctx)
    r2 = cb.build_family_units(run, "A", ctx)
    a1 = r1["units"]["A1"]
    assert len(a1) == 12 and (a1["status"] == "resolved").all() and (a1["Y"] == 1.0).all()
    assert a1["d"].min() >= 1.0
    pd.testing.assert_frame_equal(a1, r2["units"]["A1"])
    assert r1["n_markets_read"] == 12
    # census mode: no outcome columns are ever loaded and no outcome is attached
    c = cb.build_family_units(run, "A", ctx, census=True)
    assert "Y" not in c["units"]["A1"].columns and len(c["units"]["A1"]) == 12
    assert not set(cb.OUTCOME_COLUMNS) & set(cb.load_sample(run, census=True).columns)
    with pytest.raises(ValueError):
        cb.assert_no_outcome_columns(cb.load_sample(run))


def test_dry_run_never_reads_outcomes(tmp_path):
    run, ctx = build_run(tmp_path, n=6)
    sample = pd.read_csv(run / "sample.csv.gz", dtype=str, keep_default_na=False)
    sample["outcome_prices"] = "NOT-AN-OUTCOME"
    sample["uma_status"] = "NOT-AN-OUTCOME"
    _gz(run / "sample.csv.gz", sample.to_csv(index=False))
    fr = cb.evaluate_family(run, "A", ctx, stage=1, n_boot=20, n_placebo=2, placebo_y=True)
    assert fr.tests["A1"]["n"] == 0 or fr.tests["A1"]["testable"] is False  # 6 units: not testable, but it ran


def test_family_e_requires_text(tmp_path):
    run, ctx = build_run(tmp_path, n=3)
    sample = pd.read_csv(run / "sample.csv.gz", dtype=str, keep_default_na=False).drop(columns=["question", "outcomes"])
    _gz(run / "sample.csv.gz", sample.to_csv(index=False))
    with pytest.raises(cb.Refused):
        cb.build_family_units(run, "E", ctx)


def test_build_family_e_counts_exclusions_by_outcome(tmp_path):
    cre = END - 60 * DAY
    ok = {"id": "e0", "created": cre, "end": cre + 30 * DAY, "close": cre + 20 * DAY, "closed": 1, "outcome_prices": '["0","1"]',
          "question": "Will Donald Trump be arrested?", "prices": price_series(cre, cre + 31 * DAY, 0.4),
          "trades": [(cre + 100 * (k + 1), "BUY", 5, 0.4, 0) for k in range(3)]}
    trunc = {**ok, "id": "e1", "trades": ok["trades"][:2], "truncated": True, "oldest": cre + 100, "outcome_prices": '["1","0"]'}
    run = write_run(tmp_path, "h2_main", [ok, trunc], END + 300 * DAY)
    r = cb.build_family_units(run, "E", ctx_for())
    assert len(r["units"]["E1"]) == 1 and len(r["units"]["E3"]) == 1 and len(r["units"]["E2"]) == 1
    assert r["units"]["E1"]["sensational"].iloc[0]
    assert r["excluded"]["E1"][0]["y_tag"] == "lose"  # token 1 (NO) held, YES paid -> NO loses
    assert r["units"]["E1"]["Y"].iloc[0] == 1.0 and "drift" in r["units"]["E1"].columns


# ----------------------------------------------------------------------------------------------- guards: fail closed
def test_forbidden_runs():
    for rid in ("h3_power", "h4_seal", "h4_seal_v2", "h1_first"):
        with pytest.raises(cb.Refused):
            cb.forbid_run(rid)
    cb.forbid_run("h2_main")
    cb.forbid_run("h5_cb1")


def test_missing_request_clock_refuses(tmp_path):
    (tmp_path / "h2_main").mkdir()
    (tmp_path / "h2_main" / "manifest.json").write_text("{}")
    with pytest.raises(cb.Refused):
        cb.make_ctx(tmp_path / "h2_main")


def good_spec(tmp_path) -> Path:
    p = tmp_path / "spec.json"
    cb.write_spec(p)
    return p


def test_declaration_spec_guard(tmp_path):
    with pytest.raises(cb.Refused):
        cb.require_declaration(tmp_path / "missing.json", require_committed=False)
    p = good_spec(tmp_path)
    assert cb.require_declaration(p, require_committed=False) == cb.declaration_sha256()
    with pytest.raises(FileExistsError):
        cb.write_spec(p)
    spec = json.loads(p.read_text())
    spec["declaration_sha256"] = "0" * 64
    p.write_text(json.dumps(spec))
    with pytest.raises(cb.Refused):
        cb.require_declaration(p, require_committed=False)
    # a spec that exists but is not committed to git is refused by default (tmp_path is outside the repo)
    spec["declaration_sha256"] = cb.declaration_sha256()
    p.write_text(json.dumps(spec))
    with pytest.raises(cb.Refused, match="not committed"):
        cb.require_declaration(p)


def seal_dir(root: Path, name="h5_cb1") -> tuple[Path, Path]:
    run = write_run(root, name, [a1_market("s1")], END + 300 * DAY)
    h5_seal.seal_run(run, trials_path=root / "seal_trials.jsonl")
    copy = root / "h5_cb1_SEAL.json"
    copy.write_text(json.dumps({"listing_sha256": json.loads((run / "SEAL.json").read_text())["listing_sha256"]}))
    return run, copy


def test_screen_refuses_before_seal(tmp_path):
    spec = good_spec(tmp_path)
    h2 = write_run(tmp_path, "h2_main", [a1_market()], END + 300 * DAY)
    h5 = write_run(tmp_path, "h5_cb1", [a1_market("s1")], END + 300 * DAY)
    missing_copy = tmp_path / "no_seal_copy.json"
    with pytest.raises(cb.Refused, match="seal copy"):  # committed seal copy missing
        cb.screen(h2, ["A"], spec_path=spec, seal_copy=missing_copy, require_committed=False, h5_run_dir=h5)
    copy = tmp_path / "copy.json"
    copy.write_text("{}")
    with pytest.raises(cb.Refused, match="seal"):  # h5 run exists but is not sealed
        cb.screen(h2, ["A"], spec_path=spec, seal_copy=copy, require_committed=False, h5_run_dir=h5)
    with pytest.raises(cb.Refused):  # no declaration spec
        cb.screen(h2, ["A"], spec_path=tmp_path / "none.json", seal_copy=copy, require_committed=False, h5_run_dir=h5)
    with pytest.raises(cb.Refused):  # screen never runs on h5
        cb.screen(h5, ["A"], spec_path=spec, seal_copy=copy, require_committed=False, h5_run_dir=h5)
    assert not any((tmp_path / "h2_main").glob("cb1/results*"))


def test_screen_runs_when_sealed_and_modified_h5_refuses(tmp_path):
    spec = good_spec(tmp_path)
    h2 = write_run(tmp_path, "h2_main", [a1_market(f"m{i}") for i in range(3)], END + 300 * DAY)
    h5, copy = seal_dir(tmp_path)
    out = cb.screen(h2, ["A"], spec_path=spec, seal_copy=copy, require_committed=False, h5_run_dir=h5, n_boot=20, n_placebo=2)
    assert set(out["tests"]) == {"A1", "A2"} and out["declaration_sha256"] == cb.declaration_sha256()
    assert out["advanced"] == [] and out["tests"]["A1"]["testable"] is False  # 3 markets
    (h5 / "prices" / "s1.csv.gz").write_bytes(b"tampered")
    with pytest.raises(cb.Refused):
        cb.screen(h2, ["A"], spec_path=spec, seal_copy=copy, require_committed=False, h5_run_dir=h5, n_boot=20, n_placebo=2)


def test_replicate_guards_and_access_log(tmp_path, monkeypatch):
    spec = good_spec(tmp_path)
    decl = cb.declaration_sha256()
    nothing = {"declaration_sha256": decl, "advanced": []}
    # nothing advanced: returns None and never touches h5 (the directory does not even exist)
    assert cb.replicate(tmp_path / "h5_cb1", nothing, ["A"], spec_path=spec, require_committed=False) is None
    adv = {"declaration_sha256": decl, "advanced": ["A1"]}
    with pytest.raises(cb.Refused):  # advanced but the h5 run is unsealed
        cb.replicate(write_run(tmp_path / "u", "h5_cb1", [a1_market()], END + 300 * DAY), adv, ["A"], spec_path=spec,
                     seal_copy=tmp_path / "x.json", require_committed=False)
    with pytest.raises(cb.Refused):  # screen results from another declaration
        cb.replicate(tmp_path / "h5_cb1", {"declaration_sha256": "bad", "advanced": ["A1"]}, ["A"], spec_path=spec, require_committed=False)
    with pytest.raises(cb.Refused):  # only h5_cb1 is replicated (not h2, not the ladders run)
        cb.replicate(tmp_path / "h2_main", adv, ["A"], spec_path=spec, require_committed=False)
    with pytest.raises(cb.Refused):
        cb.replicate(tmp_path / "h5_cb1_ladders", adv, ["A"], spec_path=spec, require_committed=False)
    run, copy = seal_dir(tmp_path / "ok")
    monkeypatch.setattr(cb, "evaluate_family", lambda *a, **k: cb.FamilyResult("A"))
    out = cb.replicate(run, adv, ["A"], spec_path=spec, seal_copy=copy, require_committed=False, job="jobx")
    assert out["stage"] == 2 and out["replicated_provisional_per_run"] == [] and "replicated" not in out
    log = [json.loads(x) for x in (run / "ACCESS_LOG.jsonl").read_text().splitlines()]
    assert len(log) == 1 and log[0]["job"] == "jobx" and log[0]["declaration_sha256"] == decl and "git_commit" in log[0]


def test_census_guards(tmp_path):
    spec = good_spec(tmp_path)
    h5 = write_run(tmp_path, "h5_cb1", [a1_market()], END + 300 * DAY)
    with pytest.raises(cb.Refused, match="h5"):
        cb.census(h5, spec_path=spec, require_committed=False)
    h2 = write_run(tmp_path, "h2_main", [a1_market()], END + 300 * DAY)
    with pytest.raises(cb.Refused, match="E3"):  # E3 hash not committed before text is read
        cb.census(h2, spec_path=tmp_path / "none.json", require_committed=False)
    res = cb.census(h2, spec_path=spec, require_committed=False)
    assert res["census"]["A"]["A1"]["units"] == 1 and "Y" not in json.dumps(res["census"])


def test_load_books_fails_closed(tmp_path):
    with pytest.raises(cb.Refused):
        cb.load_books(tmp_path / "none.csv.gz")
    pd.DataFrame({"market_id": ["1"], "origin_ts": [1.0]}).to_csv(tmp_path / "b.csv.gz", index=False)
    with pytest.raises(cb.Refused):
        cb.load_books(tmp_path / "b.csv.gz")


def test_seal_roundtrip_and_tamper(tmp_path):
    run, copy = seal_dir(tmp_path)
    assert cb.require_sealed(run, copy)["n_files"] > 0
    copy.write_text(json.dumps({"listing_sha256": "0" * 64}))
    with pytest.raises(cb.Refused):
        cb.require_sealed(run, copy)
    with pytest.raises(cb.Refused):
        cb.require_sealed(tmp_path / "unsealed", copy)


def test_fetch_text_requires_e3_hash_and_never_overwrites(tmp_path):
    run = write_run(tmp_path, "h2_main", [a1_market("1"), a1_market("2")], END + 300 * DAY)
    calls = []

    def tr(url, params):
        calls.append(params)
        return 200, json.dumps([{"id": 1, "question": "Will X?", "outcomes": '["Yes", "No"]'}]).encode(), {}

    with pytest.raises(cb.Refused):
        cb.fetch_text(run, tr, spec_path=tmp_path / "none.json", require_committed=False)
    assert not calls
    spec = good_spec(tmp_path)
    res = cb.fetch_text(run, tr, spec_path=spec, require_committed=False, rps=1000.0)
    assert res["n_text"] == 1 and res["n_missing_text"] == 1 and calls[0]["id"] == ["1", "2"]
    tx = pd.read_csv(run / "cb1" / "text.csv.gz", dtype=str, keep_default_na=False)
    assert tx.loc[tx.market_id == "1", "question"].iloc[0] == "Will X?" and tx.loc[tx.market_id == "2", "question"].iloc[0] == ""
    with pytest.raises(cb.Refused):
        cb.fetch_text(run, tr, spec_path=spec, require_committed=False, rps=1000.0)


def test_write_new_never_overwrites(tmp_path):
    p = tmp_path / "r.json"
    cb.write_new(p, {"a": 1})
    with pytest.raises(FileExistsError):
        cb.write_new(p, {"a": 2})


# ----------------------------------------------------------------------------------------------- trial logging and counting
def fake_tests(fam, ids, placebo=True):
    tests = {}
    for t in ids:
        tests[t] = {"id": t, "family": fam, "kind": cb.HYPOTHESES_CB1[t]["kind"], "sign_tested": cb.HYPOTHESES_CB1[t]["direction"],
                    "effect": 0.01, "p": 0.5, "advance": t == ids[0], "testable": True, "n": 200, "n_event": 100, "stage": 1,
                    "placebo": {"n_draws": 200, "advance_rate": 0.0} if placebo else {"n_draws": 0}}
    return tests


def test_trial_counts_one_line_per_test_and_count_line(tmp_path, monkeypatch):
    for k in ("cb1_history", "cb1_history_replication", "cb1_history_descriptive"):
        monkeypatch.setitem(battery2.KIND_RULES, k, (battery2.EXCLUDE, "cb1 per-test lines; counted via ml_explain n_tests"))
    trials = tmp_path / "trials.jsonl"
    path = tmp_path / "res.json"
    out = {"run_id": "h2_main", "families": ["A", "E"], "cumulative_count": 7,
           "tests": {**fake_tests("A", ["A1", "A2"]), **fake_tests("E", ["E1", "E2", "E3"])}}
    cb.write_results_and_log(out, path, replication=False, trials_path=trials)
    recs = [json.loads(x) for x in trials.read_text().splitlines()]
    kinds = [r["kind"] for r in recs]
    assert kinds.count("cb1_history") == 10  # 5 test lines + 5 placebo lines
    tests_lines = [r for r in recs if r["kind"] == "cb1_history" and r["evidence_role"] != "placebo"]
    assert len(tests_lines) == 5 and all(r["evidence_role"] == "exploratory_historical" for r in tests_lines)
    placebos = [r for r in recs if r["evidence_role"] == "placebo"]
    assert len(placebos) == 5  # carry... every fake test carried a placebo block
    counts = [r for r in recs if r["kind"] == "ml_explain"]
    assert sorted(r["source"] for r in counts) == ["creative_batch_1:A", "creative_batch_1:E"]
    assert sorted(r["n_tests"] for r in counts) == [2, 3]
    assert all(r["declaration_sha256"] == cb.declaration_sha256() and r["results_sha256"] == cb.provenance.sha256_file(path) for r in recs)
    # both counters agree: the cumulative count rises by exactly the number of tests (5), placebos count 0
    assert battery2.cumulative_count(trials)["total"] == 5
    # replication lines use their own kind and the same one-count-line rule
    out2 = {"run_id": "h5_cb1", "families": ["A"], "tests": fake_tests("A", ["A1"])}
    cb.write_results_and_log(out2, tmp_path / "rep.json", replication=True, trials_path=trials)
    assert battery2.cumulative_count(trials)["total"] == 6
    assert "cb1_history_replication" in {json.loads(x)["kind"] for x in trials.read_text().splitlines()}
    cb.log_descriptive(path, "A1 sports descriptive", "h2_main", trials)
    assert battery2.cumulative_count(trials)["total"] == 6


def test_results_file_never_overwritten_by_logging(tmp_path):
    out = {"run_id": "h2_main", "families": ["A"], "tests": fake_tests("A", ["A1"], placebo=False)}
    cb.write_results_and_log(out, tmp_path / "r.json", replication=False, trials_path=tmp_path / "t.jsonl")
    with pytest.raises(FileExistsError):
        cb.write_results_and_log(out, tmp_path / "r.json", replication=False, trials_path=tmp_path / "t.jsonl")
    assert len((tmp_path / "t.jsonl").read_text().splitlines()) == 2  # 1 test + 1 count line, none from the refused rerun


def test_declaration_hash_is_stable_and_covers_the_text_rule(monkeypatch):
    h = cb.declaration_sha256()
    assert h == cb.declaration_sha256() and len(h) == 64
    monkeypatch.setattr(cb, "VERB_RE", cb.VERB_RE + "|x")
    assert cb.declaration_sha256() != h
    assert math.isfinite(cb.HYPOTHESES_CB1["A1"]["floor_net"])
    assert [t for f in cb.FAMILY_TESTS.values() for t in f] == list(cb.HYPOTHESES_CB1)


def test_parse_families():
    assert cb.parse_families("e, A") == ["A", "E"]
    with pytest.raises(cb.Refused):
        cb.parse_families("B")
    assert cb.results_name(["E", "A"], False) == "results_cb1_AE.json" and cb.results_name(["C"], True) == "results_cb1_C_rep.json"


# ----------------------------------------------------------------------------------------------- freeze-check fixes 3-8, 12
def test_tail_gate_excludes_censored_from_pi_and_reports_censored_as_loser():
    df = long_units(n=600, lose=[1, 2, 3, 4, 5])
    cens = np.zeros(600, bool)
    cens[300:500] = True
    df.loc[cens, "status"] = "censored"
    df.loc[cens, "censored"] = True
    ti = cb.tail_inputs(df, "A")
    assert len(ti["losses"]) == 400 and ti["n_censored"] == 200 and len(ti["clusters"]) == 400
    g = cb.gate_core(df, cb.HYPOTHESES_CB1["A1"], 0.01, n_boot=50)
    t = g["tail"]
    assert t["n"] == 400 and t["pi_hat"] == pytest.approx(5 / 400) and t["n_censored_excluded"] == 200
    assert t["censored_as_loser"]["pi_hat"] == pytest.approx(205 / 600)  # worst case, reported only
    assert t["censored_as_loser"]["ok"] is False


def test_lookback_rule_counts_excluded_units_and_a2_not_a_survivor_sample(tmp_path):
    ms = [a1_market(f"in{i}", close=END + (2 + i) * DAY) for i in range(3)]
    ms += [a1_market(f"out{i}", close=END + (2 + i) * DAY, created=END - 600 * DAY) for i in range(2)]
    run = write_run(tmp_path, "h2_main", ms, END + 300 * DAY)
    ctx = ctx_for()
    assert ctx.lookback_d == 450.0
    b = cb.build_family_units(run, "A", ctx)
    assert sorted(b["units"]["A1"]["market_id"]) == ["in0", "in1", "in2"]
    lb = b["lookback_excluded"]
    assert lb["markets_outside"] == 2 and lb["would_qualify"]["A1"] == 2 and lb["lookback_days"] == 450.0
    assert cb.in_lookback({"created_epoch": float("nan")}, ctx) is False


def test_units_with_no_asof_price_are_counted_by_status(tmp_path):
    created = END - 10 * DAY
    stale = dict(prices=price_series(created, END - 5 * DAY, 0.97))  # last price long before every origin
    ms = [a1_market("r1", **stale), a1_market("r2", **stale), a1_market("u1", closed=0, close=None, **stale)]
    ms[2]["close"] = ""
    run = write_run(tmp_path, "h2_main", ms, END + 300 * DAY)
    b = cb.build_family_units(run, "A", ctx_for())
    assert b["no_asof_price_by_status"]["A1"] == {"resolved": 2, "unresolved": 1}
    assert len(b["units"]["A1"]) == 0


def test_missing_outcome_as_losing_worst_case():
    df = long_units(n=300)
    raw = pd.concat([df, long_units(n=20).assign(market_id=[f"x{i}" for i in range(20)], event=[f"y{i}" for i in range(20)],
                                                status="missing", Y=np.nan, net=np.nan)], ignore_index=True)
    r = cb.missing_as_losing(df, raw)
    a, f = float(df["a"].iloc[0]), float(df["f"].iloc[0])
    assert r["n_missing"] == 20
    assert r["mean"] == pytest.approx((df["net"].sum() - 20 * (a + f)) / 320)
    assert cb.missing_as_losing(df, df)["n_missing"] == 0


def _hist_rep(tests, stage=2):
    return {"stage": stage, "revision": cb.REVISION_R, "tests": tests}


def _hist_screen(advanced):
    return {"stage": 1, "revision": cb.REVISION, "tests": {t: {"p": 0.01, "advance": True} for t in advanced}}


def test_batch_holm_over_both_modules_and_refusals():
    s1 = [("hs", _hist_screen(["A1", "E1"])), ("dd", {"window": "dev", "tests": {"D2": {"p": 0.1, "advance": True},
                                                                              "D1": {"p": 0.5, "advance": False}}})]
    docs = [
        ("h", _hist_rep({"A1": {"p": 0.001, "advance": True}, "E1": {"p": 0.03, "advance": True}})),
        ("d", {"window": "rep", "tests": {"D2": {"p": 0.01, "advance": True}}}),
        ("b", {"stage": "stage2_pre_holm", "tests": {"B1": {"p": 0.2, "advance": False}, "B2": {"p": 1.0, "advance": False}}}),
    ]
    r = cb.batch_holm(docs, stage1_docs=s1)
    assert r["m"] == 5 and r["replicated"] == ["A1", "D2"]  # E1: 0.03 > 0.05/3
    assert r["missing_stage2_counted_p1"] == [] and r["expected_family"] == ["A1", "B1", "B2", "D2", "E1"]
    assert r["tests"]["E1"]["replicated"] is False and r["tests"]["A1"]["p_holm"] == pytest.approx(0.005)
    # reject only counts if the test's own Stage-2 gate passed
    docs2 = [("h", _hist_rep({"A1": {"p": 0.001, "advance": False}}))]
    assert cb.batch_holm(docs2, stage1_docs=s1)["replicated"] == []
    for bad in ({"window": "dev", "tests": {"D1": {"p": 0.1}}}, _hist_rep({"A1": {"p": 0.1}}, stage=1),
                {"tests": {"B3": {"p": 0.1}}}):
        with pytest.raises(cb.Refused):
            cb.batch_holm([("x", bad)], stage1_docs=s1)
    with pytest.raises(cb.Refused, match="both"):
        cb.batch_holm([("h", _hist_rep({"A1": {"p": 0.1}})), ("h2", _hist_rep({"A1": {"p": 0.1}}))], stage1_docs=s1)


def test_batch_holm_family_missing_stage2_counts_p1_and_unexpected_refused():
    s1 = [("hs", _hist_screen(["A1", "E1"]))]
    # E1 advanced at Stage 1 but has no Stage-2 result; B2 is always in the family: both p = 1 and listed
    r = cb.batch_holm([("h", _hist_rep({"A1": {"p": 0.001, "advance": True}})),
                       ("b", {"stage": "stage2_pre_holm", "tests": {"B1": {"p": 0.0001, "advance": True}}})], stage1_docs=s1)
    assert r["m"] == 4 and r["missing_stage2_counted_p1"] == ["B2", "E1"]
    assert r["tests"]["E1"]["p"] == 1.0 and r["tests"]["E1"]["replicated"] is False
    # Holm over m = 4 (not 2): B1 is rank 1, A1 rank 2 => p_holm = 3 * 0.001
    assert r["tests"]["A1"]["p_holm"] == pytest.approx(0.003) and r["replicated"] == ["A1", "B1"]
    # a Stage-2 test that did not advance at Stage 1 is refused (C1 not in the expected list)
    with pytest.raises(cb.Refused, match="not in the expected family"):
        cb.batch_holm([("h", _hist_rep({"C1": {"p": 0.001, "advance": True}}))], stage1_docs=s1)
    # a Stage-2 file as Stage-1 input is refused
    with pytest.raises(cb.Refused, match="Stage-1"):
        cb.batch_holm([], stage1_docs=[("x", _hist_rep({"A1": {"p": 0.1}}))])
    assert "batch_holm_family" in cb.declaration_blob() and "h2_completeness" in cb.declaration_blob()


def test_h2_make_ctx_requires_manifest_lookback_days(tmp_path):
    run = tmp_path / "h2_main"
    run.mkdir()
    for manifest in ({}, {"lookback_days": None}, {"lookback_days": "x"}, {"lookback_days": -3}):
        (run / "manifest.json").write_text(json.dumps({**manifest, "request_clock_now": iso(END)}))
        with pytest.raises(cb.Refused, match="lookback_days"):
            cb.make_ctx(run)
    (run / "manifest.json").write_text(json.dumps({"lookback_days": 700, "request_clock_now": iso(END)}))
    assert cb.make_ctx(run).lookback_d == 700.0


def test_h2_make_ctx_reads_lookback_days_from_manifest_params(tmp_path):
    run = tmp_path / "h2_main"
    run.mkdir()
    base = {"request_clock_now": iso(END)}
    (run / "manifest.json").write_text(json.dumps({**base, "params": {"lookback_days": 270}}))
    assert cb.make_ctx(run).lookback_d == 270.0
    # top-level wins when both are present
    (run / "manifest.json").write_text(json.dumps({**base, "lookback_days": 100, "params": {"lookback_days": 270}}))
    assert cb.make_ctx(run).lookback_d == 100.0
    for params in ({}, {"lookback_days": None}, {"lookback_days": "x"}, {"lookback_days": 0}):
        (run / "manifest.json").write_text(json.dumps({**base, "params": params}))
        with pytest.raises(cb.Refused, match="lookback_days"):
            cb.make_ctx(run)


def _runner():
    import importlib.util

    spec = importlib.util.spec_from_file_location("run_cb1_history", Path(__file__).resolve().parents[2] / "scripts" / "run_cb1_history.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_replicate_writes_nothing_under_the_sealed_run_dir(tmp_path, monkeypatch, capsys):
    r = _runner()
    root = tmp_path / "history"
    spec = good_spec(tmp_path)
    run, copy = seal_dir(root)
    orig = cb.replicate
    monkeypatch.setattr(cb, "replicate", lambda *a, **k: orig(*a, seal_copy=copy, spec_path=spec, require_committed=False, **k))
    before = h5_seal.list_files(run)
    out_root = tmp_path / "creative_batch1" / "history"
    screen_dir = out_root / "h2_main"
    screen_dir.mkdir(parents=True)
    (screen_dir / cb.results_name(["A"], False)).write_text(json.dumps({"declaration_sha256": cb.declaration_sha256(), "advanced": ["A1"]}))
    monkeypatch.setattr(cb, "evaluate_family", lambda *a, **k: cb.FamilyResult("A"))
    monkeypatch.setattr(cb, "write_results_and_log", lambda out, path, **k: cb.write_new(path, out))
    assert r.main(["replicate", "--run-id", "h5_cb1", "--family", "A", "--root", str(root), "--out-root", str(out_root)]) == 0
    assert (out_root / "h5_cb1" / cb.results_name(["A"], True)).exists()
    assert h5_seal.list_files(run) == before  # no file added under the sealed dir (ACCESS_LOG is unlisted)
    h5_seal.verify_seal(run)
    # default out dir is outside the run dir too; an --out-root inside it is refused
    ns = type("A", (), {"root": str(root), "run_id": "h5_cb1", "out_root": None})()
    assert root.resolve() not in r.out_dir(ns).resolve().parents
    ns.out_root = str(run.parent)
    with pytest.raises(cb.Refused, match="inside the run directory"):
        r.out_dir(ns)
    capsys.readouterr()


def test_runner_batch_holm_writes_outside_and_never_overwrites(tmp_path, capsys):
    r = _runner()
    f = tmp_path / "rep.json"
    f.write_text(json.dumps(_hist_rep({"A1": {"p": 0.001, "advance": True}})))
    d = tmp_path / "dev.json"
    d.write_text(json.dumps(_hist_screen(["A1"])))
    out = tmp_path / "bh.json"
    assert r.main(["batch-holm", "--results", str(f), "--out", str(out)]) == 2  # --stage1 is required
    assert r.main(["batch-holm", "--stage1", str(d), "--results", str(f), "--out", str(out)]) == 0
    doc = json.loads(out.read_text())
    assert doc["replicated"] == ["A1"] and doc["missing_stage2_counted_p1"] == ["B1", "B2"]
    assert r.main(["batch-holm", "--stage1", str(d), "--results", str(f), "--out", str(out)]) == 2  # never overwritten


def test_seal_copy_accepts_only_the_one_file_per_run_format(tmp_path):
    run, copy = seal_dir(tmp_path)
    assert cb.require_sealed(run, copy)["listing_sha256"]
    lst = json.loads(copy.read_text())["listing_sha256"]
    for layout in ({"runs": {"h5_cb1": {"listing_sha256": lst}}}, {"runs": [{"run_id": "h5_cb1", "listing_sha256": lst}]}, {}):
        copy.write_text(json.dumps(layout))
        with pytest.raises(cb.Refused):
            cb.require_sealed(run, copy)
