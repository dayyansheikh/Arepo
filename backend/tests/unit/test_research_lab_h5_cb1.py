# ruff: noqa: E501
"""CB1-F: h5_cb1 backfill options, ladders fetch, seal/verify. Fake transports only, no network."""

from __future__ import annotations

import hashlib
import json
import math
import random
from datetime import UTC, datetime, timedelta

import pytest

from astrolabe.research_lab import h5_ladders, h5_seal, if_h2
from astrolabe.research_lab import history_backfill as hb

NOW = 1_790_000_000.0
KEY = b"k" * 32


# ------------------------------------------------------------------ default behaviour unchanged
def _mk(i, closed):
    return {"id": str(i), "conditionId": f"0xc{i}", "clobTokenIds": json.dumps([f"a{i}", f"b{i}"]),
            "closed": closed, "feeType": "sports_fees" if i % 2 else None, "volumeNum": 1000.0 * i,
            "liquidityNum": 1.0, "startDate": f"2026-0{1 + i % 9}-05T00:00:00Z",
            "createdAt": f"2026-0{1 + i % 9}-04T00:00:00Z", "endDate": "2026-09-20T00:00:00Z",
            "closedTime": "2026-09-21 00:00:00+00", "events": [{"id": f"e{i % 4}", "title": f"Will Trump win {i}"}],
            "question": f"Will Trump win {i}?", "slug": f"s{i}"}


def _golden_transport(calls):
    def tr(url, params):
        key = sorted((k, str(v)) for k, v in params.items())
        calls.append((url, key))
        h = int(hashlib.sha256(json.dumps(key).encode()).hexdigest(), 16)
        if params.get("offset", 0) > 0 or h % 3 == 0:
            return 200, b"[]", {}
        n = 100 if h % 5 == 0 else 7
        return 200, json.dumps([_mk(h % 1000 * 100 + j, params.get("closed") == "true")
                                for j in range(n)]).encode(), {}
    return tr


def _h(x):
    return hashlib.sha256(x.encode()).hexdigest()[:16]


def test_default_frame_sampling_and_plans_unchanged_golden():
    """Golden values were produced by the pre-CB1 module (git HEAD before this change) on the same
    fake transport: request sequence, frame rows, frame report, samples and price windows."""
    calls: list = []
    lim = hb.Limiter(_golden_transport(calls), rps=1000, sleep=lambda s: None)
    rows, rep = hb.fetch_frame(lim, NOW, lookback_days=4, seed="g", with_text=False)
    assert len(calls) == 65 and _h(json.dumps(calls)) == "9b5bb74ac78540b8"
    assert _h(json.dumps(sorted(rows, key=lambda r: r["market_id"]), default=str,
                         sort_keys=True)) == "cb64cc3aa5b366b8"
    assert _h(json.dumps(rep, sort_keys=True, default=str)) == "52c2c88c5edb1e3a"
    assert "windows_dropped_capped" not in rep and "outcomes" not in rows[0]
    calls.clear()
    lim = hb.Limiter(_golden_transport(calls), rps=1000, sleep=lambda s: None)
    rows, _ = hb.fetch_frame(lim, NOW, lookback_days=4, seed="g", with_text=True)
    assert _h(json.dumps(sorted(rows, key=lambda r: r["market_id"]), default=str,
                         sort_keys=True)) == "8e86b45e5cfeda6a"
    s, _ = hb.draw_sample(rows, 20, "g")
    assert _h(json.dumps([x["market_id"] for x in s])) == "4f181565219783a2"
    s, _ = hb.draw_sample_weighted(rows, 20, "g", 3.0)
    assert _h(json.dumps([(x["market_id"], x["inclusion_prob"]) for x in s])) == "edbb2508d33c69d8"
    assert _h(json.dumps([hb.price_window(x, NOW, 120) for x in rows])) == "bc78e5fd6dc052be"
    # default window plan: price_windows("min", 0) == the legacy single window
    for r in rows:
        w = hb.price_window(r, NOW, 120)
        assert hb.price_windows(r, NOW, 120) == ([w] if w else [])


# ------------------------------------------------------------------ frame options
def _day_windows(seed, day, windows_per_day=6, minutes=15):
    rng = random.Random(f"{seed}|{day:%Y-%m-%d}")
    return sorted(rng.sample(range(1440 // minutes), windows_per_day))


def test_forward_walk_uses_same_seeded_windows_and_closed_only():
    calls: list = []
    lim = hb.Limiter(_golden_transport(calls), rps=1000, sleep=lambda s: None)
    hb.fetch_frame(lim, NOW, lookback_days=1, seed="g", closed_future_days=2)
    day0 = datetime.fromtimestamp(NOW, UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    first = [p for u, p in calls if u == hb.GAMMA_MARKETS and dict(p).get("offset") == "0"]
    for d in (1, 2):  # future days
        day = day0 + timedelta(days=d)
        want = {(day + timedelta(minutes=15 * k)).strftime("%Y-%m-%dT%H:%M:%SZ")
                for k in _day_windows("g", day)}
        got = {dict(p)["end_date_min"] for p in first if "end_date_min" in dict(p)
               and dict(p)["end_date_min"][:10] == f"{day:%Y-%m-%d}"}
        assert got == want
        assert not any("start_date_min" in dict(p) and dict(p)["start_date_min"][:10]
                       == f"{day:%Y-%m-%d}" for p in first)  # no active kind in the future


def test_capped_window_dropped_entirely_and_counted():
    day0 = datetime.fromtimestamp(NOW, UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    day = day0 - timedelta(days=1)
    k = _day_windows("g", day)[0]
    a = (day + timedelta(minutes=15 * k)).strftime("%Y-%m-%dT%H:%M:%SZ")

    def tr(url, params):
        off = params.get("offset", 0)
        capped_win = params.get("end_date_min") == a
        if capped_win:  # always a full page: still capped after pages_per_window pages
            rows = [_mk(900_000 + off + j, True) for j in range(100)]
        elif off == 0 and params.get("closed") == "true":
            rows = [_mk(int(params["end_date_min"][8:10]) * 1000 + int(params["end_date_min"][11:13])
                        * 10 + int(params["end_date_min"][14:16]) // 15, True)]
        else:
            rows = []
        return 200, json.dumps(rows).encode(), {}

    lim = hb.Limiter(tr, rps=1000, sleep=lambda s: None)
    rows, rep = hb.fetch_frame(lim, NOW, lookback_days=1, seed="g", pages_per_window=2,
                               drop_capped_windows=True)
    assert not [r for r in rows if int(r["market_id"]) >= 900_000]
    assert rep["windows_dropped_capped"] == {"closed": 1, "active": 0}
    assert rep["rows_in_dropped_windows"] == 200
    assert rep["dropped_capped_by_day"] == {f"{day:%Y-%m-%d}": {"closed": 1, "active": 0}}
    lim = hb.Limiter(tr, rps=1000, sleep=lambda s: None)
    rows2, rep2 = hb.fetch_frame(lim, NOW, lookback_days=1, seed="g", pages_per_window=2)
    assert len([r for r in rows2 if int(r["market_id"]) >= 900_000]) == 200  # default keeps them
    assert rep2["windows_capped"]["closed"] == 1


def test_pages_per_window_20_reads_2000_rows_before_capping():
    seen = []

    def tr(url, params):
        seen.append(params.get("offset", 0))
        return 200, json.dumps([_mk(params.get("offset", 0) + j + 1, True) for j in range(100)]).encode(), {}

    lim = hb.Limiter(tr, rps=1000, sleep=lambda s: None)
    rows, capped = hb._paged(lim, {"closed": "true"}, max_rows=20 * hb.GAMMA_PAGE)
    assert capped and len(rows) == 2000 and max(seen) == 1900


# ------------------------------------------------------------------ sampling
def _frow(i, status, topic, month, q="q"):
    return {"market_id": str(i), "status": status, "topic": topic, "created_at": f"{month}-03",
            "question": q, "event_title": "", "slug": ""}


def test_cb1_weights_creation_known_and_inclusion_prob():
    frame = ([_frow(i, "closed", "crypto", "2026-01", "BTC Up or Down - 5 min") for i in range(400)]
             + [_frow(1000 + i, "closed", "politics", "2026-01") for i in range(400)]
             + [_frow(2000 + i, "closed", "sports", "2026-01") for i in range(400)]
             + [_frow(3000 + i, "closed", "crypto", "2026-01", "Bitcoin above 100k?") for i in range(400)])
    # no volume / liquidity / outcome / price keys exist on these rows: the sampler must not read them
    chosen, rep = hb.draw_sample_cb1(frame, 400, "s")
    by = {}
    for r in chosen:
        by.setdefault(r["stratum"].split("|")[1], []).append(r)
    n = {k: len(v) for k, v in by.items()}
    assert set(n) == {"crypto_updown", "politics", "sports", "crypto"}
    assert n["crypto_updown"] / n["sports"] == pytest.approx(0.25, abs=0.03)
    assert n["politics"] / n["sports"] == pytest.approx(1.5, abs=0.05)
    for r in chosen:
        assert r["inclusion_prob"] * r["sample_weight"] == pytest.approx(1.0)
    assert sum(1 / r["sample_weight"] * 400 * 0 + 1 for r in chosen) == 400
    # exclusion removes ids before strata are formed
    chosen2, rep2 = hb.draw_sample_cb1(frame, 400, "s", {r["market_id"] for r in chosen})
    assert not {r["market_id"] for r in chosen} & {r["market_id"] for r in chosen2}
    assert rep2["excluded_prior_ids"] == 400


# ------------------------------------------------------------------ price windows
def _mrow(closed=True, start=NOW - 300 * 86400, close=NOW - 100 * 86400, end=NOW - 150 * 86400):
    return {"closed": int(closed), "start_epoch": start, "close_epoch": close if closed else float("nan"),
            "end_epoch": end}


def test_head_days_adds_exactly_one_window_and_only_when_tail_misses_listing():
    r = _mrow()
    base = hb.price_windows(r, NOW, 120, "close_or_end_max", 0)
    assert len(base) == 1
    with_head = hb.price_windows(r, NOW, 120, "close_or_end_max", 8)
    assert len(with_head) == 2 and with_head[0] == (int(r["start_epoch"]), int(r["start_epoch"]) + 8 * 86400)
    assert with_head[1] == base[0]
    short = _mrow(start=NOW - 110 * 86400, close=NOW - 100 * 86400)  # tail reaches the listing
    assert len(hb.price_windows(short, NOW, 120, "close_or_end_max", 8)) == 1


def test_close_or_end_max_extends_only_closed_markets():
    r = _mrow(end=NOW - 50 * 86400, close=NOW - 150 * 86400)  # end later than close
    assert hb.price_window(r, NOW, 120)[1] == int(NOW - 150 * 86400 + 86400)
    assert hb.price_windows(r, NOW, 120, "close_or_end_max")[0][1] == int(NOW - 50 * 86400 + 86400)
    act = _mrow(closed=False, end=NOW + 10 * 86400)  # active, end not yet passed: tail only
    assert hb.price_windows(act, NOW, 120, "close_or_end_max") == hb.price_windows(act, NOW, 120)
    fut = _mrow(end=NOW + 300 * 86400, close=NOW - 5 * 86400)  # scheduled far ahead, closed early
    assert hb.price_windows(fut, NOW, 120, "close_or_end_max")[0][1] == int(NOW)
    with pytest.raises(ValueError):
        hb.price_windows(r, NOW, 120, "bogus")


def _gap(wins, a, b):
    cur = a
    for x, y in sorted(wins):
        if x > cur + 1:
            break
        cur = max(cur, y)
    return cur < b - 1


@pytest.mark.parametrize("close_d", [-20, -60, -100, -149, -200, None])  # None = active
def test_h5_price_coverage_of_created_to_end_independent_of_close_time(close_d):
    """Fix 1: created T-200d, end T-150d. Coverage of [created, end+1d] must hold whether the market
    closed at T-20d (the reviewer's repro), earlier, or is still active."""
    day = 86400
    r = {"closed": int(close_d is not None), "start_epoch": NOW - 200 * day,
         "close_epoch": NOW + close_d * day if close_d is not None else float("nan"),
         "end_epoch": NOW - 150 * day}
    w = hb.price_windows(r, NOW, 120, "close_or_end_max", 8)
    assert not _gap(w, r["start_epoch"], r["end_epoch"] + day), w
    if close_d is not None and close_d > -149:  # the post-end tail is still fetched
        assert w[-1][1] == int(min(NOW + close_d * day + day, NOW))
    # A2-style 90-day life closing late: [end-?]: coverage of the whole life up to end+1d
    r2 = {**r, "start_epoch": NOW - 240 * day, "end_epoch": NOW - 150 * day}
    w2 = hb.price_windows(r2, NOW, 120, "close_or_end_max", 8)
    assert not _gap(w2, r2["start_epoch"], r2["end_epoch"] + day), w2


def test_h5_active_market_with_past_end_has_end_window():
    day = 86400
    r = {"closed": 0, "start_epoch": NOW - 400 * day, "close_epoch": float("nan"),
         "end_epoch": NOW - 130 * day}
    w = hb.price_windows(r, NOW, 120, "close_or_end_max", 8)
    assert not _gap(w, r["end_epoch"] + day - 120 * day, r["end_epoch"] + day)
    assert w[-1][1] == int(NOW)  # and the live tail
    # the h2 plan is unchanged
    assert hb.price_windows(r, NOW, 120) == [hb.price_window(r, NOW, 120)]


# ------------------------------------------------------------------ fix 2: T_fetch cap, T_seal
def test_fetch_trades_caps_at_ts_cap_and_counts_dropped():
    page = [{"timestamp": t, "side": "BUY", "size": 1, "price": 0.5, "outcomeIndex": 0,
             "proxyWallet": "0xabc", "transactionHash": f"h{t}", "asset": "a"} for t in (50, 100, 150, 200)]

    class L:
        def get(self, url, params):
            return 200, page if params["offset"] == 0 else []

    rows, st = hb.fetch_trades(L(), "c", KEY, 100, ts_cap=120)
    assert [r[0] for r in rows] == [50, 100] and st["dropped_post_cap"] == 2
    rows, st = hb.fetch_trades(L(), "c", KEY, 100)  # no cap (h2 path): all kept, no count
    assert len(rows) == 4 and st["dropped_post_cap"] is None


def TradesAfterClock():
    fake = Fake()
    base = fake.__call__

    def call(url, params):
        if url == hb.DATA_TRADES:
            ts = [int(NOW) - 100, int(NOW) + 500, int(NOW) + 900]  # two after T_fetch
            return 200, json.dumps([{"timestamp": t, "side": "BUY", "size": 1, "price": 0.4,
                                     "outcomeIndex": 0, "proxyWallet": "0xabc",
                                     "transactionHash": f"h{t}", "asset": "a"} for t in ts]).encode(), {}
        return base(url, params)
    return call


def test_cb1_run_drops_post_tfetch_trades_and_records_counts(tmp_path):
    import pandas as pd

    _prior_run(tmp_path, "old", ["1"])
    m = _cb1(tmp_path, TradesAfterClock())
    assert m["counts"]["trades"] == 5 and m["counts"]["trades_dropped_post_tfetch"] == 10
    t = pd.read_csv(next((tmp_path / "h5t" / "trades").glob("*.csv.gz")))
    assert list(t["ts"]) == [int(NOW) - 100]
    rec = json.loads((tmp_path / "h5t" / "progress.jsonl").read_text().splitlines()[0])
    assert rec["trades_dropped_post_tfetch"] == 2 and rec["windows"]


def test_cb1_refuses_new_chunk_after_t_seal(tmp_path):
    _prior_run(tmp_path, "old", ["1"])
    fake = Fake()
    m = _cb1(tmp_path, fake, wall_clock=lambda: hb.T_SEAL_EPOCH)  # at T_seal: refused up front
    assert m["stopped"].startswith("t_seal_passed") and not fake.calls
    assert not (tmp_path / "h5t").exists() or not (tmp_path / "h5t" / "manifest.json").exists()
    # passing T_seal mid-chunk stops before the next market
    clock = {"n": 0}

    def wc():
        clock["n"] += 1
        return hb.T_SEAL_EPOCH - 10 if clock["n"] <= 3 else hb.T_SEAL_EPOCH + 1

    m = _cb1(tmp_path, Fake(), wall_clock=wc)
    assert m["stopped"].startswith("t_seal_passed") and m["counts"]["markets_done"] < 5


def test_ladders_refuses_after_t_seal(tmp_path):
    from datetime import datetime as dt

    m = h5_ladders.ladders_fetch(
        tmp_path, "h5l", lambda *a: (404, b"", {}), start=dt(2024, 1, 1, tzinfo=UTC),
        end=dt(2024, 1, 2, tzinfo=UTC), exclude_runs=[], ifh2_ladder_file=None, key=KEY,
        wall_clock=lambda: hb.T_SEAL_EPOCH + 1)
    assert m["stopped"] == "t_seal_passed"


def test_paged_error_is_capped_only_when_requested():
    pages = [(200, [{"id": i} for i in range(hb.GAMMA_PAGE)]), (500, None)]

    class L:
        def __init__(self):
            self.i = 0

        def get(self, url, params):
            r = pages[min(self.i, 1)]
            self.i += 1
            return r

    rows, capped = hb._paged(L(), {}, max_rows=10**6)
    assert len(rows) == hb.GAMMA_PAGE and capped is False  # legacy
    rows, capped = hb._paged(L(), {}, max_rows=10**6, error_is_capped=True)
    assert capped is True


def _load_cli():
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location(
        "cb1_h5_cli", Path(__file__).resolve().parents[2] / "scripts" / "cb1_h5.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_selfcheck_and_h2_coverage_counter(tmp_path):

    import pandas as pd

    cli = _load_cli()
    cli.check_window_logic()
    assert cli.main(["selfcheck"]) == 0
    day = 86400
    d = tmp_path / "h2_main"
    d.mkdir()
    rows = [
        # closed late, window anchored on close: misses the end-anchored span
        {"market_id": "1", "closed": 1, "start_epoch": NOW - 200 * day, "end_epoch": NOW - 150 * day, "close_epoch": NOW - 20 * day},
        # covered
        {"market_id": "2", "closed": 1, "start_epoch": NOW - 100 * day, "end_epoch": NOW - 50 * day, "close_epoch": NOW - 50 * day},
        {"market_id": "3", "closed": 0, "start_epoch": NOW - 400 * day, "end_epoch": NOW - 130 * day, "close_epoch": ""},
    ]
    pd.DataFrame(rows).to_csv(d / "sample.csv.gz", index=False)
    (d / "manifest.json").write_text(json.dumps({"request_clock_now": datetime.fromtimestamp(NOW, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")}))
    wins = {"1": [NOW - 139 * day, NOW - 19 * day], "2": [NOW - 100 * day, NOW - 49 * day], "3": [NOW - 120 * day, NOW]}
    with open(d / "progress.jsonl", "w") as fh:
        for mid, w in wins.items():
            fh.write(json.dumps({"market_id": mid, "status": "done", "window": w}) + "\n")
    out = cli.count_h2_coverage(tmp_path, "h2_main")
    assert out["by_status"]["closed"]["units"] == 2 and out["by_status"]["closed"]["miss_end_anchor"] == 1
    assert out["by_status"]["active"]["miss_end_anchor"] == 1 and out["by_status"]["active"]["miss_full_interval"] == 1
    assert out["by_status"]["closed"]["miss_full_interval"] == 1
    assert sorted(p.name for p in d.iterdir()) == ["manifest.json", "progress.jsonl", "sample.csv.gz"]  # read-only


# ------------------------------------------------------------------ full cb1 run: budget, resume
class Fake:
    def __init__(self, n=6):
        self.markets = [_mk(i, True) for i in range(1, n + 1)]
        for m in self.markets:
            m["outcomes"] = '["Yes", "No"]'
        self.calls = []

    def __call__(self, url, params):
        self.calls.append(url)
        if url == hb.GAMMA_MARKETS:
            ok = params.get("closed") == "true" and params.get("offset", 0) == 0
            return 200, json.dumps(self.markets if ok else []).encode(), {}
        if url == hb.CLOB_PRICES:
            pts = [{"t": t, "p": 0.5} for t in range(int(params["startTs"]), int(params["endTs"]), 3600)]
            return 200, json.dumps({"history": pts}).encode(), {}
        if url == hb.DATA_TRADES:
            return 200, json.dumps([]).encode(), {}
        return 404, b"", {}


def _prior_run(root, run_id, ids):
    import pandas as pd

    d = root / run_id
    d.mkdir(parents=True)
    pd.DataFrame({"market_id": ids}).to_csv(d / "sample.csv.gz", index=False)


def _cb1(tmp_path, fake, **kw):
    kw.setdefault("wall_clock", lambda: NOW)  # before T_seal whatever the real date
    return hb.run(tmp_path, "h5t", fake, n_markets=5, key=KEY, now=NOW, sleep=lambda s: None,
                  lookback_days=2, closed_future_days=1, strata_profile="cb1", pages_per_window=20,
                  price_end="close_or_end_max", head_days=8, live_check=None, rps=9,
                  exclude_runs=["old"], **kw)


def test_cb1_run_budget_stop_resume_and_columns(tmp_path):
    _prior_run(tmp_path, "old", ["1"])
    fake = Fake()
    m = _cb1(tmp_path, fake, budget_min=1e-12)  # already out of budget: frame pauses, resumable
    assert "budget reached" in m["stopped"]
    m = _cb1(tmp_path, fake)
    assert m["stopped"] is None and m["counts"]["markets_done"] == 5  # market 1 excluded
    import pandas as pd

    s = pd.read_csv(tmp_path / "h5t" / "sample.csv.gz", dtype=str)
    assert {"outcomes", "inclusion_prob", "sample_weight", "topic", "question"} <= set(s.columns)
    assert "1" not in set(s.market_id)
    assert m["params"]["strata_profile"] == "cb1" and m["params"]["max_rps"] == 4.0
    assert m["frame_report"]["closed_future_days"] == 1
    assert json.loads((tmp_path / "h5t" / "request_clock.json").read_text())["request_clock_epoch"] == NOW
    # resume of a finished run does no new market work
    n_prices = fake.calls.count(hb.CLOB_PRICES)
    _cb1(tmp_path, fake)
    assert fake.calls.count(hb.CLOB_PRICES) == n_prices


def test_cb1_budget_stops_between_markets_then_resumes(tmp_path):
    _prior_run(tmp_path, "old", ["1"])
    fake = Fake()
    clock = {"t": 0.0}
    real_time = hb.time.time
    seen = {"n": 0}

    def fake_time():
        return clock["t"]

    orig_fetch_trades = hb.fetch_trades

    def counting(*a, **k):
        seen["n"] += 1
        clock["t"] += 100.0  # each market "takes" 100 s
        return orig_fetch_trades(*a, **k)

    hb.time.time = fake_time
    hb.fetch_trades = counting
    try:
        m = _cb1(tmp_path, fake, budget_min=3.0)  # 180 s budget -> 2 markets
        assert m["stopped"] == "budget reached" and m["counts"]["markets_done"] == 2
        clock["t"] = 0.0
        m = _cb1(tmp_path, fake, budget_min=3.0)
        assert m["counts"]["markets_done"] == 4 and m["stopped"] == "budget reached"
        clock["t"] = 0.0
        m = _cb1(tmp_path, fake, budget_min=30.0)
        assert m["counts"]["markets_done"] == 5 and m["stopped"] is None
    finally:
        hb.time.time = real_time
        hb.fetch_trades = orig_fetch_trades
    assert seen["n"] == 5  # no market fetched twice


def test_cb1_refuses_when_excluded_run_sample_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        _cb1(tmp_path, Fake())


def test_cb1_stops_cleanly_at_disk_cap(tmp_path):
    _prior_run(tmp_path, "old", ["1"])
    m = _cb1(tmp_path, Fake(), disk_cap=3000, budget_scope="run")
    assert m["stopped"] and "disk_budget" in m["stopped"]


def test_collector_lock_probe(tmp_path):
    import fcntl
    import os

    lock = tmp_path / "c.lock"
    assert hb.collector_lock_busy(str(lock)) is False  # absent: never created, not busy
    assert not lock.exists()
    fd = os.open(lock, os.O_RDWR | os.O_CREAT)
    fcntl.flock(fd, fcntl.LOCK_EX)
    try:
        # same-process flock on a different open file description conflicts
        assert hb.collector_lock_busy(str(lock)) is True
    finally:
        os.close(fd)
    assert hb.collector_lock_busy(str(lock)) is False


# ------------------------------------------------------------------ seal / verify / access log
def _fake_run(tmp_path, stopped=None):
    d = tmp_path / "h5x"
    (d / "prices").mkdir(parents=True)
    (d / "prices" / "1.csv.gz").write_bytes(b"abc")
    (d / "sample.csv.gz").write_bytes(b"sample")
    (d / "manifest.json").write_text(json.dumps({
        "run_id": "h5x", "stopped": stopped, "request_clock_now": "2026-10-16T12:00:00Z",
        "frame_report": {"windows_dropped_capped": {"closed": 2, "active": 0},
                         "rows_in_dropped_windows": 7, "dropped_capped_by_day": {}}}))
    return d


def test_seal_verify_roundtrip_and_tamper_detection(tmp_path):
    d = _fake_run(tmp_path)
    trials = tmp_path / "trials.jsonl"
    with pytest.raises(h5_seal.SealError):
        h5_seal.require_sealed(d)  # not sealed yet
    seal = h5_seal.seal_run(d, trials_path=trials)
    assert seal["n_files"] == 3 and seal["capped_window_exclusions"]["rows_in_dropped_windows"] == 7
    assert seal["request_clock_now"] == "2026-10-16T12:00:00Z"
    assert (d / "ACCESS_LOG.jsonl").read_text() == ""
    line = json.loads(trials.read_text().splitlines()[-1])
    assert line["kind"] == "history_seal_declaration" and line["listing_sha256"] == seal["listing_sha256"]
    assert h5_seal.verify_seal(d)["listing_sha256"] == seal["listing_sha256"]
    with pytest.raises(h5_seal.SealError):  # never rewritten
        h5_seal.seal_run(d, trials_path=trials)
    # modified file
    (d / "prices" / "1.csv.gz").write_bytes(b"abd")
    with pytest.raises(h5_seal.SealError, match="modified"):
        h5_seal.require_sealed(d)
    (d / "prices" / "1.csv.gz").write_bytes(b"abc")
    h5_seal.verify_seal(d)
    # extra file, missing file
    (d / "prices" / "2.csv.gz").write_bytes(b"x")
    with pytest.raises(h5_seal.SealError, match="extra"):
        h5_seal.verify_seal(d)
    (d / "prices" / "2.csv.gz").unlink()
    (d / "sample.csv.gz").unlink()
    with pytest.raises(h5_seal.SealError, match="missing"):
        h5_seal.verify_seal(d)
    (d / "sample.csv.gz").write_bytes(b"sample")
    # tampered seal table / declaration
    sp = d / "SEAL.json"
    good = sp.read_text()
    obj = json.loads(good)
    obj["declaration"]["read_rules"] = "anything goes"
    sp.write_text(json.dumps(obj))
    with pytest.raises(h5_seal.SealError, match="declaration"):
        h5_seal.verify_seal(d)
    sp.write_text(good)
    h5_seal.verify_seal(d)


def test_seal_refuses_unfinished_run(tmp_path):
    d = _fake_run(tmp_path, stopped="budget reached")
    with pytest.raises(h5_seal.SealError, match="unfinished"):
        h5_seal.seal_run(d, trials_path=tmp_path / "t.jsonl")
    assert not (d / "SEAL.json").exists()


def test_committed_seal_is_one_file_per_run_named_run_id_SEAL(tmp_path):
    d = _fake_run(tmp_path)
    seals = tmp_path / "seals"
    h5_seal.seal_run(d, trials_path=tmp_path / "t.jsonl")
    p = h5_seal.write_committed_copy(d, seals)
    assert p == seals / "h5x_SEAL.json" == h5_seal.committed_seal_path("h5x", seals)
    doc = json.loads(p.read_text())
    assert p.read_bytes() == (d / "SEAL.json").read_bytes() and doc["run_id"] == "h5x"
    assert doc["listing_sha256"] == h5_seal.verify_seal(d)["listing_sha256"]
    assert h5_seal.write_committed_copy(d, seals) == p  # idempotent
    h5_seal.read_sealed(d, "j", ["sample.csv.gz"], p)
    p.write_text(json.dumps({**doc, "run_id": "other"}))
    with pytest.raises(h5_seal.SealError, match="not 'h5x'"):
        h5_seal.require_sealed(d, p)
    p.write_text(json.dumps({**doc, "listing_sha256": "0" * 64}))
    with pytest.raises(h5_seal.SealError, match="does not match"):
        h5_seal.require_sealed(d, p)
    with pytest.raises(h5_seal.SealError, match="different content"):
        h5_seal.write_committed_copy(d, seals)


def test_committed_seal_copy_must_match_and_access_log_appends(tmp_path):
    d = _fake_run(tmp_path)
    seal = h5_seal.seal_run(d, trials_path=tmp_path / "t.jsonl")
    committed = tmp_path / "h5x_SEAL.json"
    with pytest.raises(h5_seal.SealError, match="committed seal copy missing"):
        h5_seal.require_sealed(d, committed)
    committed.write_text(json.dumps({"listing_sha256": "0" * 64}))
    with pytest.raises(h5_seal.SealError, match="does not match"):
        h5_seal.require_sealed(d, committed)
    committed.write_text(json.dumps({"listing_sha256": seal["listing_sha256"]}))
    paths = h5_seal.read_sealed(d, "q0024_test", ["prices/*.csv.gz"], committed)
    assert [p.name for p in paths] == ["1.csv.gz"]
    h5_seal.read_sealed(d, "q0025_test", ["sample.csv.gz"], committed)
    log = [json.loads(x) for x in (d / "ACCESS_LOG.jsonl").read_text().splitlines()]
    assert [x["job"] for x in log] == ["q0024_test", "q0025_test"]
    assert log[0]["files"] == ["prices/*.csv.gz"] and log[0]["declaration_sha256"] == seal["declaration_sha256"]
    assert {"utc", "git_commit"} <= set(log[0])
    h5_seal.verify_seal(d)  # appending to the access log does not break the seal
    with pytest.raises(h5_seal.SealError):
        h5_seal.read_sealed(d, "j", ["nothing/*"], committed)
    (d / "sample.csv.gz").write_bytes(b"changed")
    with pytest.raises(h5_seal.SealError):
        h5_seal.read_sealed(d, "j", ["sample.csv.gz"], committed)
    assert len((d / "ACCESS_LOG.jsonl").read_text().splitlines()) == 2  # refused read not logged


def test_seal_trial_kind_is_known_to_the_counter():
    from astrolabe.research_lab import battery2

    assert battery2.KIND_RULES["history_seal_declaration"][0] == battery2.EXCLUDE


# ------------------------------------------------------------------ ladders fetch
def _event(eid, title, deadlines, cid0=0):
    ms = []
    for k, (txt, _gi) in enumerate(deadlines):
        ms.append({"id": str(eid * 10 + k), "conditionId": f"0xcond{eid}{k}",
                   "question": f"Will {title} happen by {txt}?", "groupItemTitle": txt,
                   "clobTokenIds": json.dumps([f"y{eid}{k}", f"n{eid}{k}"]), "negRisk": False,
                   "createdAt": "2024-02-01T00:00:00Z", "closedTime": "2024-08-01 00:00:00+00",
                   "closed": True, "outcomePrices": '["0", "1"]', "outcomes": '["Yes","No"]',
                   "endDate": "2024-09-01T00:00:00Z"})
    return {"id": str(eid), "title": title, "negRisk": False, "markets": ms}


class LadderFake:
    def __init__(self, events, prices=True):
        self.events, self.prices = events, prices
        self.calls = []

    def __call__(self, url, params):
        self.calls.append(url)
        if url == if_h2.GAMMA_EVENTS:
            params = dict(params) if isinstance(params, dict) else {k: v for k, v in params}
            if params.get("offset", 0) != 0:
                return 200, b"[]", {}
            return 200, json.dumps(self.events).encode(), {}
        if url == hb.CLOB_PRICES:
            h = [{"t": t, "p": 0.3} for t in range(int(params["startTs"]), int(params["endTs"]), 3600)]
            return 200, json.dumps({"history": h if self.prices else []}).encode(), {}
        if url == hb.DATA_TRADES:
            return 200, b"[]", {}
        return 404, b"", {}


def _ifh2_file(tmp_path, ladders):
    p = tmp_path / "if_h2_ladders.jsonl.gz"
    if_h2.save_jsonl_gz(p, ladders)
    return p


def test_ladder_guards_drop_ifh2_and_history_overlap():
    lads = [{"ladder_id": "1:a", "event_id": "1", "rungs": [{"market_id": "10"}, {"market_id": "11"}]},
            {"ladder_id": "2:a", "event_id": "2", "rungs": [{"market_id": "20"}, {"market_id": "21"}]},
            {"ladder_id": "3:a", "event_id": "3", "rungs": [{"market_id": "30"}, {"market_id": "31"}]},
            {"ladder_id": "4:a", "event_id": "4", "rungs": [{"market_id": "40"}, {"market_id": "41"}]}]
    kept, rep = h5_ladders.apply_guards(lads, {"1"}, {"21"}, {"31"})
    assert [x["ladder_id"] for x in kept] == ["4:a"]
    assert (rep["dropped_ifh2_event"], rep["dropped_ifh2_rung"], rep["dropped_history_sample"]) == (1, 1, 1)


def _lf(tmp_path, fake, **kw):
    return h5_ladders.ladders_fetch(
        tmp_path, "lad", fake, start=datetime(2024, 1, 1, tzinfo=UTC), end=datetime(2024, 1, 15, tzinfo=UTC),
        exclude_runs=["old"], ifh2_ladder_file=_ifh2_file(tmp_path, [
            {"ladder_id": "9:x", "event_id": "9", "rungs": [{"market_id": "90"}]}]),
        key=KEY, now=1_730_000_000.0, sleep=lambda s: None, live_check=None, **kw)


def test_ladders_fetch_resume_guards_and_completion(tmp_path):
    _prior_run(tmp_path, "old", ["9999"])
    events = [_event(1, "alpha", [("June 30", 0), ("July 31", 0)]),
              _event(9, "ifh2event", [("June 30", 0), ("July 31", 0)])]
    fake = LadderFake(events)
    m = _lf(tmp_path, fake, budget_min=1e-12)  # no budget: probe passes, then stops before rung 1
    assert m["stopped"] == "budget reached"
    assert m["guards"]["dropped_ifh2_event"] == 1 and m["n_ladders"] == 1 and m["n_rungs"] == 2
    ev_calls = fake.calls.count(if_h2.GAMMA_EVENTS)
    m = _lf(tmp_path, fake)
    assert m["token"] == h5_ladders.COMPLETE_TOKEN and m["counts"]["rungs_done"] == 2
    assert fake.calls.count(if_h2.GAMMA_EVENTS) == ev_calls  # walk not repeated
    assert (tmp_path / "lad" / "prices" / "10.csv.gz").exists()
    assert (tmp_path / "lad" / "trades" / "11.csv.gz").exists()
    assert m["request_clock_now"].startswith("2024-") or m["request_clock_now"].startswith("2025-")
    assert (tmp_path / "lad" / "request_clock.json").exists()
    h5_seal.seal_run(tmp_path / "lad", trials_path=tmp_path / "t.jsonl")


def test_ladders_probe_failure_stops_and_is_recorded(tmp_path):
    _prior_run(tmp_path, "old", ["9999"])
    events = [_event(1, "alpha", [("June 30", 0), ("July 31", 0)])]
    m = _lf(tmp_path, LadderFake(events, prices=False))
    assert m["token"] == h5_ladders.PROBE_FAILED_TOKEN and m["probe"]["passed"] is False
    assert not (tmp_path / "lad" / "prices").exists()
    assert math.isclose(m["probe"]["share"], 0.0)
    assert h5_seal.seal_run(tmp_path / "lad", trials_path=tmp_path / "t.jsonl")["n_files"] > 0


def test_ladders_missing_ifh2_file_fails_loudly_not_disk_budget(tmp_path):
    _prior_run(tmp_path, "old", ["9999"])
    fake = LadderFake([_event(1, "alpha", [("June 30", 0), ("July 31", 0)])])
    with pytest.raises(FileNotFoundError, match="IF-H2 ladder file missing"):
        h5_ladders.ladders_fetch(
            tmp_path, "lad", fake, start=datetime(2024, 1, 1, tzinfo=UTC), end=datetime(2024, 1, 15, tzinfo=UTC),
            exclude_runs=["old"], ifh2_ladder_file=tmp_path / "nope" / "ladders.jsonl.gz",
            key=KEY, now=1_730_000_000.0, sleep=lambda s: None, live_check=None)


def test_ladders_missing_excluded_run_sample_fails_loudly(tmp_path):
    fake = LadderFake([_event(1, "alpha", [("June 30", 0), ("July 31", 0)])])
    with pytest.raises(FileNotFoundError, match="excluded run"):
        _lf(tmp_path, fake)  # run "old" was never created


def test_history_default_root_is_absolute_repo_root():
    assert hb.DEFAULT_ROOT.is_absolute()
    assert hb.DEFAULT_ROOT.parts[-3:] == ("data-dumps", "research_lab", "history")
    assert (hb.DEFAULT_ROOT.parents[2] / "backend" / "astrolabe").is_dir()
