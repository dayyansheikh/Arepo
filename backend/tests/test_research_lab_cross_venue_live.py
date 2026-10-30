"""Unit tests for the live cross-venue prospective test (no network)."""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime

import pytest

from astrolabe.research_lab import cross_venue_live as cvl
from astrolabe.research_lab import economics as econ


def _spec():
    m = {
        "m0": {"intercept": 0.0, "r1": 0.0, "r6": 0.0, "lvl": 0.0, "lvl2": 0.0},
        "m1": {
            "intercept": 0.0,
            "r1": 0.0,
            "r6": 0.0,
            "lvl": 0.0,
            "lvl2": 0.0,
            "gap": 0.0,
            "dk1": 0.5,
            "dk6": 0.0,
        },
    }
    return {"models": {"10": m, "20": m, "60": m}, "_sha256": "x" * 64}


def _pair(i=1):
    return {
        "pid": f"K{i}|P{i}",
        "k_ticker": f"K{i}",
        "token0": f"T{i}",
        "p_event_id": f"E{i}",
        "fee_rate": 0.04,
    }


class FakeLim:
    def __init__(self, k_book):
        self.k_book, self.requests, self.throttled = k_book, 0, 0
        self.state = {}

    def get(self, url, params):
        self.requests += 1
        if url.endswith("/markets"):
            ms = []
            for t in params["tickers"].split(","):
                b, a = self.state.get(t, (0.40, 0.42))
                ms.append(
                    {
                        "ticker": t,
                        "yes_bid_dollars": str(b),
                        "yes_ask_dollars": str(a),
                        "status": "active",
                    }
                )
            return 200, {"markets": ms}
        if url.endswith("/books"):
            out = []
            for d in params:
                b, a = self.state.get(d["token_id"], (0.40, 0.42))
                out.append(
                    {
                        "asset_id": d["token_id"],
                        "bids": [{"price": "0.1", "size": "5"}, {"price": str(b), "size": "10"}],
                        "asks": [{"price": "0.9", "size": "5"}, {"price": str(a), "size": "7"}],
                        "timestamp": "1700000000000",
                    }
                )
            return 200, out
        raise AssertionError(url)


def test_spec_is_hash_pinned_and_matches_file():
    spec = cvl.load_spec()
    assert spec["_sha256"] == cvl.SPEC_SHA256
    assert set(spec["models"]) == {"10", "20", "60"}
    assert spec["models"]["20"]["m1"]["dk1"] > 0  # the historical lead
    with pytest.raises(RuntimeError):
        cvl.load_spec(sha="0" * 64)


def test_two_sided_mid_rules():
    assert cvl.two_sided_mid(0.40, 0.42) == pytest.approx(0.41)
    assert math.isnan(cvl.two_sided_mid(0.0, 0.42))
    assert math.isnan(cvl.two_sided_mid(0.40, 1.0))
    assert math.isnan(cvl.two_sided_mid(0.42, 0.40))
    assert math.isnan(cvl.two_sided_mid(0.30, 0.45))  # spread > 10c


def test_parse_book_takes_best_levels_regardless_of_order():
    q = cvl.parse_book(
        {
            "bids": [{"price": "0.30", "size": "1"}, {"price": "0.35", "size": "2"}],
            "asks": [{"price": "0.50", "size": "1"}, {"price": "0.37", "size": "3"}],
            "timestamp": "1700000000000",
        }
    )
    assert (q["p_bid"], q["p_ask"], q["p_bid_sz"], q["p_ask_sz"]) == (0.35, 0.37, 2.0, 3.0)
    assert q["p_book_ts"] == 1.7e9


def test_features_need_lagged_endpoints_and_range():
    t = 10_000_000
    hist = [(t - 600, 0.50, 0.40), (t - 3600, 0.45, 0.38)]
    f = cvl.features(hist, t, 0.55, 0.42)
    assert f["dk1"] == pytest.approx(0.05) and f["dk6"] == pytest.approx(0.10)
    assert f["r1"] == pytest.approx(0.02) and f["gap"] == pytest.approx(0.13)
    assert cvl.features(hist[:1], t, 0.55, 0.42) is None  # no 60-min endpoint
    assert cvl.features(hist, t, 0.99, 0.42) is None  # out of MID_RANGE
    # lookback tolerance: an entry older than t-600-240 does not count
    assert cvl.features([(t - 900, 0.5, 0.4), (t - 3600, 0.45, 0.38)], t, 0.55, 0.42) is None
    # never uses an entry newer than t - lag
    assert cvl.lookup([(t - 100, 0.9, 0.9), (t - 700, 0.5, 0.4)], t, 600) == (0.5, 0.4)


def test_taker_pnl_long_short_and_fees():
    rate = 0.04
    long_ = cvl.taker_pnl(1, 0.40, 0.42, 0.45, 0.47, rate)
    assert long_ == pytest.approx(
        0.45 - 0.42 - econ.taker_fee(1, 0.42, rate) - econ.taker_fee(1, 0.45, rate)
    )
    short = cvl.taker_pnl(-1, 0.40, 0.42, 0.35, 0.37, rate)
    assert short == pytest.approx(
        0.40 - 0.37 - econ.taker_fee(1, 0.40, rate) - econ.taker_fee(1, 0.37, rate)
    )
    assert math.isnan(cvl.taker_pnl(0, 0.4, 0.42, 0.4, 0.42, rate))
    assert cvl.taker_pnl(1, 0.40, 0.42, 0.40, 0.42, 0.0) == pytest.approx(-0.02)


def test_fee_rate_from_fee_type():
    assert cvl.fee_rate("politics_fees", True) == (0.04, "docs:politics")
    assert cvl.fee_rate("sports_fees", False)[0] == 0.0
    assert cvl.fee_rate(None, True) == (econ.MAX_DOCS_RATE, "unknown_max")


def test_evidence_role_switches_at_registration():
    assert cvl.evidence_role(2e9, None) == "prospective_unregistered"
    reg = "2026-10-12T22:00:00Z"
    t_reg = datetime(2026, 10, 12, 22, tzinfo=UTC).timestamp()
    assert cvl.evidence_role(t_reg - 1, reg) == "prospective_unregistered"
    assert cvl.evidence_role(t_reg, reg) == "prospective_confirmation"


def test_candidates_filter_two_sided_yes_no():
    assert (
        cvl.kalshi_candidate(
            {
                "ticker": "A",
                "status": "active",
                "yes_bid_dollars": "0.4",
                "yes_ask_dollars": "0.42",
                "title": "t",
            }
        )["ticker"]
        == "A"
    )
    assert (
        cvl.kalshi_candidate(
            {"ticker": "A", "status": "active", "yes_bid_dollars": "0", "yes_ask_dollars": "0.42"}
        )
        is None
    )
    ev = {
        "id": 9,
        "markets": [
            {
                "id": 1,
                "outcomes": '["Yes", "No"]',
                "clobTokenIds": '["a", "b"]',
                "active": True,
                "acceptingOrders": True,
                "enableOrderBook": True,
                "bestBid": 0.3,
                "bestAsk": 0.31,
                "question": "q",
            },
            {
                "id": 2,
                "outcomes": '["Over", "Under"]',
                "clobTokenIds": '["c", "d"]',
                "active": True,
                "acceptingOrders": True,
                "enableOrderBook": True,
                "bestBid": 0.3,
                "bestAsk": 0.31,
            },
            {
                "id": 3,
                "outcomes": '["Yes", "No"]',
                "clobTokenIds": '["e", "f"]',
                "active": True,
                "acceptingOrders": True,
                "enableOrderBook": True,
                "bestBid": 0.0,
                "bestAsk": 0.31,
            },
        ],
    }
    got = cvl.poly_candidates(ev)
    assert [g["market_id"] for g in got] == ["1"] and got[0]["token0"] == "a"


def test_select_live_pairs_prioritises_verified_and_excludes_different():
    k = [
        {
            "ticker": f"K{i}",
            "event_ticker": f"KE{i}",
            "title": f"Will Team{i} win the Alpha Cup final",
            "yes_sub": "",
            "close_time": "2026-11-01T00:00:00Z",
            "vol24": 100.0 * i,
        }
        for i in range(1, 4)
    ]
    p = [
        {
            "market_id": f"P{i}",
            "event_id": f"E{i}",
            "question": f"Will Team{i} win the Alpha Cup final",
            "item": "",
            "outcomes": ["Yes", "No"],
            "token0": f"T{i}",
            "end": "2026-11-01T00:00:00Z",
            "vol24": 100.0 * i,
            "fee_type": "sports_fees",
            "fees_enabled": True,
        }
        for i in range(1, 4)
    ]
    ver = {("K1", "P1"): {"verdict": "same"}, ("K3", "P3"): {"verdict": "different"}}
    rows = cvl.select_live_pairs(k, p, ver, cap=5)
    assert [r["pid"] for r in rows] == ["K1|P1", "K2|P2"]
    assert rows[0]["hand_verified"] and rows[1]["fee_rate"] == 0.05


def _write_pairs(root, pairs, stamp="2026-10-12T00:00:00Z"):
    (root / "pairs_current.json").write_text(json.dumps({"refreshed_utc": stamp, "pairs": pairs}))


def test_poller_writes_predictions_before_outcomes_and_outcomes_after(tmp_path):
    lim = FakeLim({})
    clock = {"t": 0.0}
    poller = cvl.Poller(lim, lim, root=tmp_path, spec=_spec(), clock=lambda: clock["t"])
    _write_pairs(tmp_path, [_pair(1)])
    t0 = 1_800_000_000 - 1_800_000_000 % 1200
    preds_seen = []
    for i in range(0, 61):  # 2 hours of 2-min cycles
        t = t0 + i * cvl.CYCLE_S
        clock["t"] = t + 1
        # Kalshi moves up 2c at t0+3600; Polymarket follows 20 min later
        k_mid_up = t >= t0 + 3600
        p_up = t >= t0 + 3600 + 1200
        lim.state["K1"] = (0.42, 0.44) if k_mid_up else (0.40, 0.42)
        lim.state["T1"] = (0.42, 0.44) if p_up else (0.40, 0.42)
        s = poller.cycle(t)
        preds_seen.append(s["predictions"])
    preds = list(cvl.read_jsonl(tmp_path / "predictions.jsonl"))
    outs = list(cvl.read_jsonl(tmp_path / "outcomes.jsonl"))
    assert preds and outs
    # first prediction only once a 60-min lookback exists
    assert min(r["t"] for r in preds) == t0 + 3600
    by_id = {r["id"]: r for r in preds}
    assert all(by_id[o["id"]]["t"] % cvl.OUTCOME_GRID_S == 0 for o in outs)
    for o in outs:
        r = by_id[o["id"]]
        assert o["t_obs"] >= r["t"] + o["h"] * 60 - cvl.OUTCOME_TOL_S
        assert o["status"] == "evaluated"
    # signal fired at the Kalshi jump and the 20-min outcome shows the follow-through
    jump = next(r for r in preds if r["t"] == t0 + 3600)
    assert jump["f"]["dk1"] == pytest.approx(0.02) and jump["side"] == 1
    o20 = next(o for o in outs if o["id"] == jump["id"] and o["h"] == 20)
    assert o20["dp"] == pytest.approx(0.02)
    assert o20["pnl_taker"] == pytest.approx(0.42 - 0.42 - econ.taker_fee(1, 0.42, 0.04) * 2)
    assert all(r["role"] == cvl.evidence_role(r["t"]) for r in preds)


def test_outcome_unavailable_when_quote_missing(tmp_path):
    w = cvl.OutcomeWriter(tmp_path)
    r = {
        "id": "a|0",
        "pid": "a",
        "ev": "E",
        "t": 0,
        "role": "r",
        "side": 1,
        "pb": 0.4,
        "pa": 0.42,
        "fee": 0.0,
        "trade": False,
        "pm": 0.41,
    }
    n = w.update(4000, quotes=[], preds=[r])
    assert n == 3
    outs = list(cvl.read_jsonl(tmp_path / "outcomes.jsonl"))
    assert {o["status"] for o in outs} == {"unavailable"}
    # recovery does not duplicate already-written outcomes
    w2 = cvl.OutcomeWriter(tmp_path)
    w2.recover(4000)
    assert w2.update(5000) == 0


def test_retired_pairs_keep_polling_then_drop(tmp_path):
    lim = FakeLim({})
    clock = {"t": 1000.0}
    poller = cvl.Poller(lim, lim, root=tmp_path, spec=_spec(), clock=lambda: clock["t"])
    _write_pairs(tmp_path, [_pair(1), _pair(2)], "a")
    poller.load_pairs()
    _write_pairs(tmp_path, [_pair(2)], "b")
    poller.load_pairs()
    assert poller.pairs["K1|P1"].retired_at == 1000.0
    assert len(poller.active_states(1000.0 + cvl.RETIRE_KEEP_S)) == 2
    assert len(poller.active_states(1001.0 + cvl.RETIRE_KEEP_S)) == 1


def test_cap_stops_poller(tmp_path):
    lim = FakeLim({})
    poller = cvl.Poller(lim, lim, root=tmp_path, spec=_spec(), total_cap_bytes=1)
    (tmp_path / "x").write_text("xx")
    with pytest.raises(cvl.CapReached):
        poller.cycle(1200)


def test_analyze_primary_gain_uses_nonoverlapping_origins(tmp_path):
    preds, outs = [], []
    for ev in range(6):
        for k in range(20):
            t = 1_800_000_000 - 1_800_000_000 % 1200 + k * 600  # half are off the 20-min grid
            dk = 0.01 * ((k % 3) - 1)
            y = 0.5 * dk
            pid = f"p{ev}"
            r = {
                "id": f"{pid}|{t}",
                "pid": pid,
                "ev": f"E{ev}",
                "t": t,
                "role": "prospective_confirmation",
                "f": {"dk1": dk},
                "y0": {"10": 0.0, "20": 0.0, "60": 0.0},
                "y1": {"10": y, "20": y, "60": y},
                "trade": True,
                "kr": t + 2,
                "pr": t + 3,
            }
            preds.append(r)
            outs.append(
                {
                    "id": r["id"],
                    "h": 20,
                    "status": "evaluated",
                    "dp": y + 0.001,
                    "pnl_trade": -0.01,
                    "t_obs": t + 1200,
                    "p_recv": t + 1203,
                }
            )
    # a late origin (excluded), a duplicate outcome line (ignored), a late outcome quote
    late = {**preds[0], "id": "late|1", "kr": preds[0]["t"] + 500}
    preds.append(late)
    outs.append({**outs[0], "id": "late|1"})
    outs.append({**outs[2], "dp": 99.0})
    outs.append({**outs[4], "id": outs[4]["id"]})
    cvl.append_jsonl(tmp_path / "predictions.jsonl", preds)
    cvl.append_jsonl(tmp_path / "outcomes.jsonl", outs)
    res = cvl.analyze(
        tmp_path,
        start_utc="2020-01-01T00:00:00Z",
        end_utc="2030-01-01T00:00:00Z",
        n_boot=200,
        now=2e9,
    )
    h = res["horizons"]["20"]
    assert h["n_origins"] == 60 and h["n_clusters"] == 6
    assert res["origin_late"] == 1 and res["duplicate_outcome_lines"] == 2
    assert h["rel_mse_gain"] > 0.9 and h["slope_dp_on_dk1"] == pytest.approx(0.5)
    assert h["partial_slope_dk1_given_m0"] == pytest.approx(0.5)
    assert res["missing_line"][10] == 120  # 10-min grid origins without any 10-min line
    assert res["executable_pnl"]["mean_pnl_per_share"] == pytest.approx(-0.01)


def test_prefilter_keeps_every_matchable_kalshi_market():
    from astrolabe.research_lab import cross_venue as cv

    k = [
        {
            "ticker": "A",
            "event_ticker": "EA",
            "title": "Will Team Red win the Alpha Cup final 2026",
            "yes_sub": "",
            "close_time": "2026-11-01T00:00:00Z",
        },
        {
            "ticker": "B",
            "event_ticker": "EB",
            "title": "Will Team Red win the Alpha Cup final 2027",
            "yes_sub": "",
            "close_time": "2026-11-01T00:00:00Z",
        },
        {
            "ticker": "C",
            "event_ticker": "EC",
            "title": "Will Team Red win the Alpha Cup final 2026",
            "yes_sub": "",
            "close_time": "2026-12-01T00:00:00Z",
        },
        {
            "ticker": "D",
            "event_ticker": "ED",
            "title": "Unrelated words entirely here now",
            "yes_sub": "",
            "close_time": "2026-11-01T00:00:00Z",
        },
    ]
    p = [
        {
            "market_id": "P",
            "event_id": "E",
            "question": "Will Team Red win the Alpha Cup final 2026",
            "item": "",
            "outcomes": ["Yes", "No"],
            "token0": "T",
            "end": "2026-11-02T00:00:00Z",
        }
    ]
    f = cvl.MatchPrefilter(p)
    kept = [m for m in k if f(m)]
    assert [m["ticker"] for m in kept] == ["A"]
    assert cv.match_markets(kept, p) == cv.match_markets(k, p)


def test_live_conflict_words_drop_unverified_vice_president_pairs():
    k = [
        {
            "ticker": "K1",
            "event_ticker": "KE",
            "close_time": "2028-08-01T00:00:00Z",
            "vol24": 1.0,
            "title": "Will Wes Moore be the Democratic Presidential nominee in 2028?",
            "yes_sub": "",
        }
    ]
    p = [
        {
            "market_id": "P1",
            "event_id": "E",
            "outcomes": ["Yes", "No"],
            "token0": "T",
            "item": "",
            "question": "Will Wes Moore be the 2028 Democratic Vice-Presidential nominee?",
            "end": "2028-08-01T00:00:00Z",
            "vol24": 1.0,
        }
    ]
    assert cvl.select_live_pairs(k, p, {}) == []
    assert len(cvl.select_live_pairs(k, p, {("K1", "P1"): {"verdict": "same"}})) == 1


def test_restart_seeds_feature_history_from_recovered_quotes(tmp_path):
    t = 1_800_000_000
    q = [
        {"t": t - 3600, "pid": "K1|P1", "k_mid": 0.4, "p_mid": 0.4},
        {"t": t - 600, "pid": "K1|P1", "k_mid": 0.42, "p_mid": 0.4},
    ]
    day = cvl.datetime.fromtimestamp(t, cvl.UTC).strftime("%Y%m%d")
    cvl.append_jsonl(tmp_path / "quotes" / f"{day}.jsonl", q)
    lim = FakeLim({})
    poller = cvl.Poller(lim, lim, root=tmp_path, spec=_spec(), clock=lambda: t + 1)
    poller.outcomes.recover(t)
    _write_pairs(tmp_path, [_pair(1)])
    s = poller.cycle(t)
    assert s["predictions"] == 1


class PageLim:
    def __init__(self, pages):
        self.pages, self.requests, self.throttled = list(pages), 0, 0

    def get(self, url, params):
        self.requests += 1
        return 200, self.pages.pop(0)


def test_fetchers_page_until_cursor_ends():
    m = {"ticker": "A", "status": "active", "yes_bid_dollars": "0.4", "yes_ask_dollars": "0.42"}
    k, st = cvl.fetch_kalshi_open(PageLim([{"markets": [m], "cursor": "c"}, {"markets": [m]}]))
    assert len(k) == 2 and st["complete"] and st["pages"] == 2
    ev = {
        "id": 1,
        "markets": [
            {
                "id": 1,
                "outcomes": '["Yes", "No"]',
                "clobTokenIds": '["a", "b"]',
                "active": True,
                "acceptingOrders": True,
                "enableOrderBook": True,
                "bestBid": 0.3,
                "bestAsk": 0.31,
            }
        ],
    }
    mk = {**ev["markets"][0], "events": [{"id": 7}]}
    p, st = cvl.fetch_poly_open(PageLim([{"markets": [mk], "next_cursor": "x"}, {"markets": [mk]}]))
    assert p[0]["event_id"] == "7"
    assert len(p) == 2 and st["complete"]
