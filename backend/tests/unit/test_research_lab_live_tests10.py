# ruff: noqa: E501
"""LT10 (LIVE_TESTS_10.md) code tests, synthetic data only, no network, no real data-dumps read: the route-1 quotes-only successor poller (line schema
equal to E009's, refresh rule, no prediction or outcome file), the vendored bases' provenance and drift, the import ban, and the unit builders."""

from __future__ import annotations

import ast
import hashlib
import json
import math
import re
from pathlib import Path

import pytest

from astrolabe.research_lab import cross_venue as cv
from astrolabe.research_lab import cross_venue_live as e9
from astrolabe.research_lab import live_tests10 as lt
from astrolabe.research_lab import live_tests10_analysis_base as ab
from astrolabe.research_lab import live_tests10_base as b
from astrolabe.research_lab import xv_quotes_poller as xq
from astrolabe.research_lab import xv_quotes_poller_base as xb

HERE = Path(lt.__file__).resolve().parent
SCRIPTS = HERE.parents[1] / "scripts"
LT10_FILES = [*HERE.glob("live_tests10*.py"), HERE / "xv_quotes_poller.py", HERE / "xv_quotes_poller_base.py", SCRIPTS / "run_live_tests10.py",
              SCRIPTS / "run_xv_quotes_poller.py", SCRIPTS / "vendor_lt10_base.py"]

# --- the successor poller (route 1) ------------------------------------------------------------------------------------------------


class FakeLim:
    """``get(url, params) -> (status, json)``; Kalshi and CLOB answers are fixed synthetic touches."""

    def __init__(self, kind: str, tickers: dict[str, dict]) -> None:
        self.kind, self.data, self.requests, self.throttled = kind, tickers, 0, 0

    def get(self, url, params):
        self.requests += 1
        if self.kind == "k":
            want = params["tickers"].split(",")
            return 200, {"markets": [{"ticker": t, **self.data[t]} for t in want if t in self.data]}
        return 200, [self.data[d["token_id"]] for d in params if d["token_id"] in self.data]


def _pairs_doc(n: int, refreshed: str) -> dict:
    pairs = [{"pid": f"K{i}|{i}", "k_ticker": f"K{i}", "p_market_id": str(i), "token0": f"tok{i}"} for i in range(n)]
    return {"refreshed_utc": refreshed, "version": "x", "n_pairs": n, "pairs": pairs}


def _lims(n: int):
    k = {f"K{i}": {"yes_bid_dollars": "0.40", "yes_ask_dollars": "0.44", "last_price_dollars": "0.42", "yes_bid_size_fp": "10", "yes_ask_size_fp": "12",
                   "status": "active", "volume_24h_fp": "100"} for i in range(n)}
    p = {f"tok{i}": {"asset_id": f"tok{i}", "bids": [{"price": "0.41", "size": "5"}, {"price": "0.40", "size": "9"}], "asks": [{"price": "0.45", "size": "7"}],
                     "last_trade_price": "0.43", "timestamp": "1790000000000", "tick_size": "0.01", "min_order_size": "5"} for i in range(n)}
    return FakeLim("k", k), FakeLim("p", p)


def _read_lines(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text().splitlines()]


def test_successor_line_schema_equals_e009(tmp_path):
    n = 3
    t = 1790000040
    ra, rb = tmp_path / "e9", tmp_path / "xv"
    for r in (ra, rb):
        r.mkdir()
        (r / "pairs_current.json").write_text(json.dumps(_pairs_doc(n, "2026-11-01T00:00:00Z")))
    p9 = e9.Poller(*_lims(n), root=ra, spec=e9.load_spec(), clock=lambda: 1790000041.0)
    p9.cycle(t)
    pq = xq.XVQuotesPoller(*_lims(n), root=rb, clock=lambda: 1790000041.0)
    pq.cycle(t)
    day = "20261021"
    a = _read_lines(ra / "quotes" / f"{day}.jsonl") if (ra / "quotes" / f"{day}.jsonl").exists() else _read_lines(next((ra / "quotes").glob("*.jsonl")))
    c = _read_lines(next((rb / "quotes").glob("*.jsonl")))
    assert len(a) == len(c) == n
    for x, y in zip(a, c, strict=True):
        assert y.pop("src") == "xv_quotes_v1"
        assert list(x) == list(y)  # same keys, same order
        assert x == y
    assert not list(rb.glob("predictions*")) and not list(rb.glob("outcomes*"))
    assert not any("predict" in q.name or "outcome" in q.name for q in rb.rglob("*"))


def test_runs_line_after_quotes_with_load_flag(tmp_path):
    (tmp_path / "pairs_current.json").write_text(json.dumps(_pairs_doc(2, "2026-11-01T00:00:00Z")))
    p = xq.XVQuotesPoller(*_lims(2), root=tmp_path, clock=lambda: 1790000041.0)
    s1 = p.cycle(1790000040)
    s2 = p.cycle(1790000160)
    (tmp_path / "pairs_current.json").write_text(json.dumps(_pairs_doc(2, "2026-11-02T00:00:00Z")))
    s3 = p.cycle(1790000280)
    assert (s1["load"], s2["load"], s3["load"]) == (True, False, True)
    assert s1["pairs_loaded_utc"] == "2026-11-01T00:00:00Z" and s3["pairs_loaded_utc"] == "2026-11-02T00:00:00Z"
    runs = xq.read_runs(tmp_path)
    assert [r["t"] for r in runs] == [1790000040, 1790000160, 1790000280] and all(r["kind"] == "cycle" for r in runs)
    # an incomplete trailing line is skipped
    with (tmp_path / "runs.jsonl").open("ab") as fh:
        fh.write(b'{"kind":"cycle","t":17900')
    assert len(xq.read_runs(tmp_path)) == 3


def test_refresh_rule_matches_e009(tmp_path):
    cur = tmp_path / "pairs_current.json"
    cur.write_text("{}")
    import os

    now = 1790000000.0
    os.utime(cur, (now - xb.REFRESH_EVERY_S - 5, now - xb.REFRESH_EVERY_S - 5))
    assert xq.refresh_due(now, cur, False, 0.0)
    assert not xq.refresh_due(now, cur, True, 0.0)
    assert not xq.refresh_due(now, cur, False, now - 60)
    os.utime(cur, (now - 100, now - 100))
    assert not xq.refresh_due(now, cur, False, 0.0)
    assert xb.REFRESH_EVERY_S == e9.REFRESH_EVERY_S == 86400 and xb.CYCLE_S == e9.CYCLE_S == 120 and xb.MAX_PAIRS == e9.MAX_PAIRS == 200
    assert xb.CHUNK == e9.CHUNK == 100 and xb.RETIRE_KEEP_S == e9.RETIRE_KEEP_S == 22800


def _market(ticker, title, yes, bid, ask, vol, close):
    return {"ticker": ticker, "event_ticker": "EV-" + ticker, "title": title, "yes_sub_title": yes, "market_type": "binary", "status": "active",
            "yes_bid_dollars": bid, "yes_ask_dollars": ask, "volume_24h_fp": vol, "expected_expiration_time": close}


def test_select_live_pairs_same_as_e009_on_fixture():
    names = ["Arsenal", "Brighton", "Chelsea", "Everton", "Fulham"]
    kal = [{"ticker": f"KX{i}", "event_ticker": f"EV{i}", "title": f"Will {n} win the 2026 premier league title", "yes_sub": "", "close_time": "2026-12-15T00:00:00Z",
            "vol24": 100.0 + i} for i, n in enumerate(names)]
    poly = [{"market_id": str(i), "event_id": f"E{i}", "question": f"Will {n} win the 2026 premier league title", "outcomes": ["Yes", "No"], "token0": f"t{i}",
             "end": "2026-12-15T00:00:00Z", "vol24": 50.0 + i, "fee_type": None, "fees_enabled": False} for i, n in enumerate(names)]
    ra = e9.select_live_pairs(kal, poly, {})
    rb = xb.select_live_pairs(kal, poly, {})
    assert ra == rb and len(ra) >= 3


def test_refresh_requires_frozen_verdicts(tmp_path):
    bad = tmp_path / "v.json"
    bad.write_text('{"pairs": []}')
    assert xq.verified_ok() and not xq.verified_ok(bad)
    with pytest.raises(RuntimeError):
        xq.refresh(None, None, tmp_path, verified_path=bad)


def test_successor_cap_stops(tmp_path):
    (tmp_path / "pairs_current.json").write_text(json.dumps(_pairs_doc(1, "2026-11-01T00:00:00Z")))
    p = xq.XVQuotesPoller(*_lims(1), root=tmp_path, clock=lambda: 1790000041.0, total_cap_bytes=1)
    with pytest.raises(xq.CapReached):
        p.cycle(1790000040)
    assert xq.TOTAL_CAP_BYTES == int(3.0 * 1024**3)


def test_retired_pair_kept_then_dropped(tmp_path):
    (tmp_path / "pairs_current.json").write_text(json.dumps(_pairs_doc(2, "2026-11-01T00:00:00Z")))
    now = [1790000041.0]
    p = xq.XVQuotesPoller(*_lims(2), root=tmp_path, clock=lambda: now[0])
    p.cycle(1790000040)
    (tmp_path / "pairs_current.json").write_text(json.dumps(_pairs_doc(1, "2026-11-02T00:00:00Z")))
    s = p.cycle(1790000160)
    assert s["pairs"] == 2 and s["retired_polled"] == 1
    now[0] += xb.RETIRE_KEEP_S + 10
    s = p.cycle(1790000160 + xb.RETIRE_KEEP_S + 10)
    assert s["pairs"] == 1


# --- the vendored bases --------------------------------------------------------------------------------------------------------------


def _segment(text: str, node) -> str:
    if not getattr(node, "decorator_list", None):
        return ast.get_source_segment(text, node)
    lines = text.splitlines(keepends=True)
    start = min([node.lineno, *(d.lineno for d in node.decorator_list)])
    return "".join(lines[start - 1:node.end_lineno]).rstrip("\n")


def _nodes(tree):
    out = {}
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
            out[n.name] = n
        elif isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    out[t.id] = n
        elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
            out[n.target.id] = n
    return out


@pytest.mark.parametrize("modname,vendored", [("live_tests10_base.py", b.VENDORED), ("xv_quotes_poller_base.py", xb.VENDORED),
                                              ("live_tests10_analysis_base.py", ab.VENDORED)])
def test_vendored_provenance_and_drift(modname, vendored):
    text = (HERE / modname).read_text()
    nodes = _nodes(ast.parse(text))
    assert len(vendored) >= 7
    src_cache = {}
    for name, v in vendored.items():
        copy_src = _segment(text, nodes[name])
        assert hashlib.sha256(copy_src.encode()).hexdigest() == v["normalised_sha256"], name
        f = v["source"]
        if f not in src_cache:
            src_cache[f] = (HERE / f).read_text()
        assert hashlib.sha256(src_cache[f].encode()).hexdigest() == v["source_sha256"], f"{f} drifted from its vendored hash (do not edit the source)"
        node = _nodes(ast.parse(src_cache[f]))[name]
        assert re.sub(v["prefix"], "", _segment(src_cache[f], node)) == copy_src, f"{name} differs from its current source"


def test_recorded_source_hashes_match_design():
    design = (HERE.parents[2] / "docs" / "research_lab" / "LIVE_TESTS_10.md").read_text()
    assert "eac14e68dc7a9d60610d9ea5d2edfdc39be73afd0192d6b41cd3d5459e5ef581" in design
    assert "5264083948a77679189f14471290c2f84bf71dac01fc9632cb0633fdb59ace99" in design
    assert hashlib.sha256((HERE / "cross_venue_live.py").read_bytes()).hexdigest() == "eac14e68dc7a9d60610d9ea5d2edfdc39be73afd0192d6b41cd3d5459e5ef581"
    assert hashlib.sha256((HERE / "cross_venue.py").read_bytes()).hexdigest() == "5264083948a77679189f14471290c2f84bf71dac01fc9632cb0633fdb59ace99"


def test_copied_constants_equal_sources():
    for name in ("MAX_SPREAD", "MID_RANGE", "LOOKBACK_TOL_S", "OUTCOME_TOL_S", "MAX_RECV_LAG_S", "OUTCOME_GRID_S", "CYCLE_S", "RETIRE_KEEP_S", "FEATURES"):
        assert getattr(b, name) == getattr(e9, name), name
    assert b.MAX_SPREAD == cv.MAX_K_SPREAD and b.MID_RANGE == cv.MID_RANGE
    for name in ("GAMMA", "CLOB", "CYCLE_S", "MAX_PAIRS", "POLY_PAGE", "CHUNK", "RETIRE_KEEP_S", "REFRESH_EVERY_S"):
        assert getattr(xb, name) == getattr(e9, name), name


def test_vendored_features_reproduce_recorded_values():
    hist = [(0.0, 0.40, 0.50), (3000.0, 0.42, 0.52), (3000.0 + 0.0, 0.42, 0.52)]
    hist = [(0.0, 0.40, 0.50), (3000.0, 0.45, 0.55)]
    f = b.features(hist, 3600.0, 0.50, 0.60)
    g = e9.features(hist, 3600.0, 0.50, 0.60)
    assert f == g and f is not None
    assert math.isclose(f["r1"], 0.60 - 0.55) and math.isclose(f["dk6"], 0.50 - 0.40) and math.isclose(f["lvl2"], 0.01)
    assert b.lookup(hist, 3600.0, 600) == (0.45, 0.55)
    assert b.two_sided_mid(0.4, 0.44) == pytest.approx(0.42) and math.isnan(b.two_sided_mid(float("nan"), 0.44))
    assert b.in_range(0.5) and not b.in_range(0.99)


def test_no_lt10_module_imports_e009_or_lt3_to_lt9():
    assert len(LT10_FILES) >= 6
    for p in LT10_FILES:
        if not p.exists():
            continue
        for node in ast.walk(ast.parse(p.read_text())):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [(node.module or "")] + [a.name for a in node.names]
            for n in names:
                assert not re.search(r"cross_venue_live|live_tests[3-9]\b|live_tests[3-9]_", n), f"{p.name} imports {n}"


# --- synthetic builders ------------------------------------------------------------------------------------------------------------------

import copy  # noqa: E402
import gzip  # noqa: E402
import subprocess  # noqa: E402
from datetime import UTC, datetime  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

T0 = 1790000400 - (1790000400 % 600)  # a multiple of 600


def mk(n=46, **over):
    """Columns of one pair 'K|1' on the 120 s grid from T0: flat quiet books; ``over`` replaces a field by an array or a callable(cols)."""
    t = T0 + 120 * np.arange(n)
    f = {"k_bid": .49, "k_ask": .51, "k_last": .50, "k_bid_sz": 100., "k_ask_sz": 100., "k_vol24": 1000., "k_recv": 1., "p_bid": .495, "p_ask": .505,
         "p_bid_sz": 100., "p_ask_sz": 100., "p_book_ts": 0., "p_tick": .01, "p_recv": 2.}
    cols = {"pid": np.array(["K|1"] * n, dtype=object), "t": t.astype(np.int64)}
    for k, v in f.items():
        cols[k] = (t + v).astype(float) if k in ("k_recv", "p_recv") else np.full(n, float(v))
    cols["k_active"] = np.ones(n, bool)
    for k, v in over.items():
        if callable(v):
            v(cols)
        elif k == "k_active":
            cols[k] = np.asarray(v, bool)
        else:
            cols[k] = np.asarray(v, float)
    return cols


def _meta(P=1, K=1, **over):
    m = {"pid": np.array([f"K|{i + 1}" for i in range(P)], dtype=object), "pair_st": np.zeros((P, K), dtype=np.int64), "cat_known": np.ones((P, K), bool),
         "sports": np.zeros((P, K), bool), "crypto": np.full((P, K), "non_crypto", dtype=object), "ev": np.full((P, K), "E1", dtype=object),
         "p_end": np.full((P, K), T0 + 1e7), "k_close": np.full((P, K), T0 + 1e7), "hv": np.zeros((P, K), bool), "exclude_event": None}
    m.update(over)
    return m


def origin(cols, j=40, **meta_over):
    A = lt.to_grid(cols, ["K|1"], T0, len(cols["t"]))
    return lt.build_origins(A, T0, np.array([j]), _meta(**meta_over)).iloc[0]


def st(r) -> str:
    return lt.STATUS_CODES[int(r.status)]


def setp(arr_name, idx, val):
    def f(cols):
        cols[arr_name][idx] = val
    return f


def _chain(*fs):
    def f(cols):
        for g in fs:
            g(cols)
    return f


# --- windows and clocks --------------------------------------------------------------------------------------------------------------


def test_quiet_flat_origin_is_a_unit():
    r = origin(mk())
    assert st(r) == "unit" and r.cls223 == 0 and r.cls222 == 3 and r.dsK == 0 and r.pull == 0 and r.s0_t == r.t - 600 and r.dec == r.t + 2


def test_s0_equals_e009_lookup():
    rng = np.random.default_rng(3)
    n = 46
    kb = 0.45 + 0.001 * rng.integers(0, 30, n)
    pb = 0.40 + 0.001 * rng.integers(0, 30, n)
    cols = mk(k_bid=kb, k_ask=kb + .02, p_bid=pb, p_ask=pb + .01)
    for i in (34, 35):  # s0 candidates j-6, j-5 invalid -> E009's lookup picks j-7
        cols["p_bid"][i] = np.nan
    r = origin(cols, j=40)
    hist = []
    for i in range(40):
        kmid, pmid = (cols["k_bid"][i] + cols["k_ask"][i]) / 2, (cols["p_bid"][i] + cols["p_ask"][i]) / 2
        if math.isfinite(pmid) and math.isfinite(kmid):
            hist.append((float(cols["t"][i]), kmid, pmid))
    t = float(cols["t"][40])
    k600, p600 = b.lookup(hist, t, 600)
    assert st(r) == "unit"
    assert r.dk1 == pytest.approx(r.kmid - k600) and r.r1 == pytest.approx(r.pmid - p600)
    assert r.s0_t == cols["t"][33]
    k3600, p3600 = b.lookup(hist, t, 3600)
    assert r.dk6 == pytest.approx(r.kmid - k3600) and r.r6 == pytest.approx(r.pmid - p3600)


def test_window_gap_below_four_polls():
    cols = mk(k_bid=_chain(*[setp("k_bid", i, np.nan) for i in (36, 37, 38, 39)]))
    r = origin(cols)
    assert st(r) == "window_gap" and r.n_win == 2
    ok = origin(mk(k_bid=_chain(*[setp("k_bid", i, np.nan) for i in (36, 37)])))
    assert st(ok) == "unit" and ok.n_win == 4


def test_decision_time_and_late_origin():
    r = origin(mk(k_recv=lambda c: c["k_recv"].__setitem__(40, c["t"][40] + 60)))
    assert st(r) == "unit" and r.dec == r.t + 60
    late = origin(mk(k_recv=lambda c: c["k_recv"].__setitem__(40, c["t"][40] + 61)))
    assert st(late) == "late_origin"
    latep = origin(mk(p_recv=lambda c: c["p_recv"].__setitem__(40, c["t"][40] + 61)))
    assert st(latep) == "late_origin"


def test_status_order_and_validity_rules():
    assert st(origin(mk(), pair_st=np.array([[lt.ST["retired"]]]))) == "retired"
    assert st(origin(mk(), pair_st=np.array([[lt.ST["not_yet_in_force"]]]))) == "not_yet_in_force"
    assert st(origin(mk(), cat_known=np.zeros((1, 1), bool))) == "category_unknown"
    assert st(origin(mk(k_ask=setp("k_ask", 40, .60)))) == "spread_censored"  # 11c spread
    assert st(origin(mk(p_bid=setp("p_bid", 40, np.nan)))) == "one_sided_p"
    assert st(origin(mk(k_bid=setp("k_bid", 40, np.nan)))) == "one_sided_k"
    assert st(origin(mk(k_active=lambda c: c["k_active"].__setitem__(40, False)))) == "one_sided_k"
    assert st(origin(mk(k_bid=_chain(setp("k_bid", 40, .97), setp("k_ask", 40, .99))))) == "out_of_range"
    sh = mk(p_bid=_chain(*[setp("p_bid", i, np.nan) for i in range(8, 11)]))  # b60 lookback poll missing -> features incomplete
    assert st(origin(sh)) == "features_incomplete"
    assert st(origin(mk(), p_end=np.full((1, 1), T0 + 40 * 120 + 7200))) == "end_soon"


def test_rv_short_and_ends_unknown_count():
    few = mk(k_bid=_chain(*[setp("k_bid", i, np.nan) for i in range(10, 26)]))
    assert st(origin(few)) == "rv_short"
    r = origin(mk(), p_end=np.full((1, 1), np.nan))
    assert st(r) == "unit" and bool(r.end_unknown)


def test_exclude_event_status():
    assert st(origin(mk(), exclude_event="E1")) == "excluded_event"
    assert st(origin(mk(), exclude_event="E9")) == "unit"


def test_target_endpoint_rule():
    n = 70
    j = np.array([40])
    tg = lt.targets(lt.to_grid(mk(n=n), ["K|1"], T0, n), T0, j, 10)
    assert int(tg.tg_status[0]) == 0 and int(tg.t_end[0]) == T0 + 50 * 120
    # exact poll missing: the nearest within +-120 s, the earlier on a tie
    c2 = mk(n=n, p_bid=_chain(setp("p_bid", 50, np.nan), setp("p_bid", 51, .60)))
    tg2 = lt.targets(lt.to_grid(c2, ["K|1"], T0, n), T0, j, 10)
    assert int(tg2.t_end[0]) == T0 + 49 * 120 and int(tg2.tg_status[0]) == 0
    # a late receipt at the exact poll (61 s) is skipped
    c3 = mk(n=n, p_recv=lambda c: c["p_recv"].__setitem__(50, c["t"][50] + 61))
    tg3 = lt.targets(lt.to_grid(c3, ["K|1"], T0, n), T0, j, 10)
    assert int(tg3.t_end[0]) == T0 + 49 * 120
    # nothing within the tolerance: no endpoint; never an endpoint before t + 1,080 s
    c4 = mk(n=n, p_bid=_chain(*[setp("p_bid", i, np.nan) for i in (49, 50, 51)]))
    tg4 = lt.targets(lt.to_grid(c4, ["K|1"], T0, n), T0, j, 10)
    assert int(tg4.t_end[0]) == -1 and int(tg4.tg_status[0]) != 0
    c5 = mk(n=n, p_bid=_chain(*[setp("p_bid", i, np.nan) for i in (49, 50, 51)]))
    c5["p_bid"][48] = .494  # poll 48 = t + 960 s is valid but lies before t + 1,080 s
    tg5 = lt.targets(lt.to_grid(c5, ["K|1"], T0, n), T0, j, 10)
    assert int(tg5.t_end[0]) == -1
    # one-sided at 50 and 49, valid at 51
    c6 = mk(n=n, p_ask=setp("p_ask", 50, np.nan), p_bid=setp("p_bid", 49, np.nan))
    tg6 = lt.targets(lt.to_grid(c6, ["K|1"], T0, n), T0, j, 10)
    assert int(tg6.t_end[0]) == T0 + 51 * 120


def test_freeze_deadline_and_late_marker(tmp_path):
    df = pd.DataFrame([origin(mk())])
    spec = lt.load_spec(sha=None)
    t = int(df.t.iloc[0])
    assert lt._write_origin(tmp_path / "a" / "live_tests10", t, df, spec, t + 1079.0) == "frozen"
    assert lt._write_origin(tmp_path / "b" / "live_tests10", t, df, spec, t + 1080.0) == "late"
    names = sorted(p.name for p in (tmp_path / "b" / "live_tests10").rglob("*.csv.gz"))
    assert any(n.endswith(".late.csv.gz") for n in names)
    assert not any(n.endswith(".late.csv.gz") for n in (p.name for p in (tmp_path / "a" / "live_tests10").rglob("*.csv.gz")))


# --- eligibility: pair records, categories ---------------------------------------------------------------------------------------------


def _rec(name, refreshed_utc, pids):
    return {"name": name, "sha256": "x", "refreshed_utc": refreshed_utc, "refreshed": lt.epoch(refreshed_utc), "stamp_ok": True, "pairs": {p: {"pid": p} for p in pids}}


def test_census_record_t_in_rule():
    R = lt.epoch("2026-10-25T00:00:00Z")
    L = lt.L_S
    keys_lo = R - 40000.0
    r1 = _rec("pairs_a.json", "2026-10-25T00:00:00Z", ["A", "B"])
    # pid A new (first line at R + 20,000 s, none in the RETIRE_KEEP_S + 120 s before R); pid B old (polled just before R)
    kt = {"A": np.array([int(R + 20000)], dtype=np.int64), "B": np.array([int(R - 600), int(R + 1000)], dtype=np.int64)}
    lt.CensusRecords([r1], kt, keys_lo=keys_lo, L=L)
    assert r1["l_obs"] == int(R + 20000) and r1["t_in"] == max(R + L, R + 20000)
    # a record is not used before T_in even though refreshed_utc is earlier
    prev = _rec("pairs_0.json", "2026-10-24T00:00:00Z", ["B"])
    nxt = _rec("pairs_a.json", "2026-10-25T00:00:00Z", ["A", "B"])
    CR2 = lt.CensusRecords([prev, nxt], kt, keys_lo=keys_lo, L=L)
    assert CR2.in_force(R + 100)["name"] == "pairs_0.json"  # nxt.refreshed <= t but T_in later
    assert CR2.in_force(R + 20000)["name"] == "pairs_a.json"
    assert CR2.pending_pids(R + 100, CR2.in_force(R + 100)) == {"A", "B"}
    # no new pid: no L_obs, T_in = refreshed + L
    r3 = _rec("pairs_c.json", "2026-10-25T00:00:00Z", ["B"])
    lt.CensusRecords([r3], kt, keys_lo=keys_lo, L=L)
    assert r3["l_obs"] is None and r3["t_in"] == R + L
    # a pid re-listed within RETIRE_KEEP_S (polled 3 h before R) is not new
    kt2 = {"A": np.array([int(R - 10800), int(R + 500)], dtype=np.int64)}
    r4 = _rec("pairs_d.json", "2026-10-25T00:00:00Z", ["A"])
    lt.CensusRecords([r4], kt2, keys_lo=keys_lo, L=L)
    assert r4["l_obs"] is None
    # look-back before the read keys: unidentifiable
    r5 = _rec("pairs_e.json", "2026-10-25T00:00:00Z", ["A"])
    lt.CensusRecords([r5], kt, keys_lo=R - 100.0, L=L)
    assert r5["l_obs"] is None and "look-back" in r5["l_obs_reason"]
    assert lt.pair_status("A", None, {"A"}) == lt.ST["not_yet_in_force"] and lt.pair_status("Z", r1, set()) == lt.ST["retired"]
    assert lt.pair_status("A", r1, set()) == lt.ST["unit"]


def test_window_rule_with_late_load_no_rewrite():
    L = lt.L_S
    r1 = _rec("pairs_20261109T000000Z.json", "2026-11-09T00:00:00Z", ["A"])
    r2 = _rec("pairs_20261110T000000Z.json", "2026-11-10T00:00:00Z", ["A", "B"])
    R2 = r2["refreshed"]
    load_t = int(R2 + L + 3600)  # the poller loads r2 late
    runs = [{"kind": "cycle", "t": t, "pairs_loaded_utc": ("2026-11-10T00:00:00Z" if t >= load_t else "2026-11-09T00:00:00Z")} for t in range(int(R2), int(R2 + L + 7200), 120)]
    W = lt.WindowRecords([r1, r2], runs, {r1["name"], r2["name"]}, L=L)
    assert r2["load_cycle"] == load_t
    t_mid = int(R2 + L + 1800)
    assert W.in_force(t_mid)["name"] == r1["name"]  # r2 is not loaded yet at t_mid, though t >= refreshed + L
    assert W.in_force(load_t - 120)["name"] == r1["name"] and W.in_force(load_t + 600)["name"] == r2["name"]
    assert W.pending_pids(t_mid, W.in_force(t_mid)) == {"A", "B"}  # r2's pids are not_yet_in_force at t_mid
    # before refreshed + L, even if loaded, r2 is not in force
    runs2 = [{"kind": "cycle", "t": t, "pairs_loaded_utc": ("2026-11-10T00:00:00Z" if t > R2 else "2026-11-09T00:00:00Z")} for t in range(int(R2), int(R2 + 600), 120)]
    W2 = lt.WindowRecords([r1, r2], runs2, {r1["name"], r2["name"]}, L=L)
    assert W2.in_force(int(R2 + 400))["name"] == r1["name"]
    # a file the reader had not seen is not in force
    W3 = lt.WindowRecords([r1, r2], runs, {r1["name"]}, L=L)
    assert W3.in_force(load_t + 600)["name"] == r1["name"]
    # the reader does not process origin t before the runs.jsonl line for cycle t exists
    assert W.ready(load_t) and not W.ready(load_t + 10**6)
    # the window never reads L_obs (it is a census-only key)
    assert "l_obs" not in r2


def test_category_rule_on_sidecar(tmp_path):
    side = tmp_path / "snapshots" / "c1"
    side.mkdir(parents=True)
    pd.DataFrame({"market_id": ["1", "2", "3"], "fee_type": ["sports_fees_v2", "x", "x"], "fee_category": ["sports", "crypto", "politics"],
                  "series_slugs": ["", "", ""]}).to_csv(side / "rows_ext.csv.gz", index=False)
    cats = lt.read_sidecar(side / "rows_ext.csv.gz")
    assert cats["1"][0] is True and cats["2"][1] == "crypto" and cats["3"] == (False, "non_crypto")
    assert lt.in_scope(False, "non_crypto", "non_sports_ex_crypto") and not lt.in_scope(True, "non_crypto", "non_sports_ex_crypto")
    assert not lt.in_scope(False, "crypto", "ex_crypto") and lt.in_scope(True, "non_crypto", "ex_crypto")
    assert not lt.in_scope(False, "unknown", "non_sports_ex_crypto")
    with pytest.raises(lt.Refused):
        lt.in_scope(False, "non_crypto", "everything")


# --- CH224 -------------------------------------------------------------------------------------------------------------------------


def test_ch224_state_fields():
    # Kalshi spread 2c at s0 (j=35) -> 4c at t (j=40): dsK = +2c; Polymarket spread 1c -> 2c
    r = origin(mk(k_bid=setp("k_bid", 40, .48), k_ask=setp("k_ask", 40, .52), p_bid=setp("p_bid", 40, .495), p_ask=setp("p_ask", 40, .515)))
    assert st(r) == "unit" and r.dsK == pytest.approx(.02) and r.sK_s0 == pytest.approx(.02) and r.sP_s0 == pytest.approx(.01)
    assert r.dsP_own == pytest.approx(.01) and r.ratio == pytest.approx(.5) and r.floorP == 0 and r.wideK == 1 and r.tightK == 0
    t2 = origin(mk(k_bid=_chain(*[setp("k_bid", i, .495) for i in range(36, 41)]), k_ask=_chain(*[setp("k_ask", i, .505) for i in range(36, 41)])))
    assert t2.dsK == pytest.approx(-.01) and t2.tightK == 1 and t2.floorK == 0
    f = origin(mk(k_bid=_chain(*[setp("k_bid", i, .495) for i in range(0, 46)]), k_ask=_chain(*[setp("k_ask", i, .505) for i in range(0, 46)])))
    assert f.floorK == 1 and f.floorP == 1  # sK(s0) = 1c, sP(t) <= p_tick


def test_ch224_scaling_and_design_matrix():
    rng = np.random.default_rng(5)
    U = pd.DataFrame({"dsK": rng.choice([-.02, -.01, 0, 0, .01, .02], 300), "dsK_tw": rng.choice([-.01, 0, .01], 300), "sign": 1.0, "hour": 3})
    X = lt.add_test_columns(U.assign(r1=0., r6=0., gap=0., dk6=0., lvl=0.), 0.01)
    assert np.allclose(X["zdsK"], U["dsK"] / 0.01) and np.allclose(X["zdsK_tw"], U["dsK_tw"] / 0.01)
    assert lt.TERM["CH224"] == "zdsK" and lt.TWIN["CH224"] == "zdsK_tw"
    ctl = lt.CONTROLS["CH224"]
    for c in ("sK_s0", "ratio", "sP_s0", "dsP_own", "floorP", "floorK", "traded", "abs_dk1", "r1", "dk6", "rv60_P", "rv60_K", "lvol", "vol_unknown", "h23"):
        assert c in ctl
    assert len([c for c in ctl if re.fullmatch(r"h\d+", c)]) == 23 and len(b.FEATURES) == 7


def test_kalshi_only_twin_loader_returns_no_polymarket_field(tmp_path):
    p = tmp_path / "data-dumps" / "research_lab" / "xv_quotes" / "quotes" / "20261110.jsonl"
    p.parent.mkdir(parents=True)
    ln = {"t": T0, "pid": "K|1", "k_bid": .49, "k_ask": .51, "p_bid": 777.0, "p_ask": 888.0, "p_bid_sz": 5.0, "k_recv": T0 + 1.0, "src": "xv_quotes_v1", "k_status": "active"}
    p.write_text(json.dumps(ln) + "\n")
    cols = lt.read_quote_file(p, lt.KALSHI_LAG_FIELDS, src="xv_quotes_v1")
    assert set(cols) <= {"pid", "t", "k_active", *[f for f in lt.KALSHI_LAG_FIELDS if f != "k_status"]}
    assert not any(k.startswith("p_") for k in cols)
    bad = dict(cols)
    bad["p_bid"] = np.array([1.0])
    with pytest.raises(lt.Refused):
        lt.overlay_kalshi(lt.to_grid(mk(), ["K|1"], T0, 46), bad, ["K|1"], T0)


def test_twins_use_kalshi_fields_only():
    n = 70
    cols = mk(n=n)
    cols["k_bid"][60], cols["k_ask"][60] = .48, .52  # Kalshi spread 2c at poll 55 (t+1800) and 4c at poll 60 (t+2400)
    wild = copy.deepcopy(cols)
    for f in ("p_bid", "p_ask", "p_bid_sz", "p_ask_sz"):
        wild[f][41:] = 123456.0
    Ak = lt.to_grid({k: v for k, v in cols.items() if not k.startswith("p_")}, ["K|1"], T0, n)
    Ak2 = lt.to_grid({k: v for k, v in wild.items() if not k.startswith("p_")}, ["K|1"], T0, n)
    j = np.array([[40]])
    tw = lt.twins(Ak, T0, j, np.array([[0]]))
    tw2 = lt.twins(Ak2, T0, j, np.array([[0]]))
    assert bool(tw.tw_ok[0]) and tw.dsK_tw[0] == pytest.approx(.02) and tw.pull_tw[0] == 1.0 and tw.traded_tw[0] == 0.0
    assert tw.equals(tw2)


# --- CH223 -------------------------------------------------------------------------------------------------------------------------


def test_ch223_every_step_quiet_condition():
    assert origin(mk()).cls223 == 0
    # the mid moves inside the window and reverts: reverted_move, not a unit of CH223
    rev = origin(mk(k_bid=setp("k_bid", 37, .50), k_ask=setp("k_ask", 37, .52)))
    assert rev.cls223 == 2 and rev.dk1 == 0
    assert lt.CLASS223[2] == "reverted_move" and lt.CLASS223[3] == "small_move"
    sm = origin(mk(k_bid=setp("k_bid", 40, .492), k_ask=setp("k_ask", 40, .512)))  # a 0.2c sub-penny move is small_move
    assert sm.cls223 == 3
    mv = origin(mk(k_bid=setp("k_bid", 40, .495), k_ask=setp("k_ask", 40, .515)))  # exactly 0.5c at t: CH222's unit, not CH223's
    assert mv.cls223 == 4 and mv.cls222 in (0, 1, 2)


def test_ch223_purity_rule_and_vol_unknown():
    tq = origin(mk(k_last=_chain(setp("k_last", 37, .51), setp("k_last", 38, .51), setp("k_last", 39, .51), setp("k_last", 40, .51))))
    assert tq.cls223 == 1 and tq.traded == 1 and tq.trade_steps == 1
    vu = origin(mk(k_vol24=_chain(*[setp("k_vol24", i, 1100.) for i in range(37, 41)])))
    assert vu.cls223 == 1 and vu.kvol_up
    vd = origin(mk(k_vol24=_chain(*[setp("k_vol24", i, 900.) for i in range(37, 41)])))  # a decrease only: no trade signal (disclosed caveat)
    assert vd.cls223 == 0 and vd.kvol_down_steps == 1
    vm = origin(mk(k_vol24=setp("k_vol24", 38, np.nan)))  # a missing step flags vol_unknown and stays in
    assert vm.cls223 == 0 and vm.vol_unknown == 1


def test_ch223_pull_edges():
    wid = origin(mk(k_bid=setp("k_bid", 40, .48), k_ask=setp("k_ask", 40, .52)))  # widening of exactly 2c, mid unchanged
    assert wid.pull == 1 and wid.cls223 == 0 and wid.pull_side == 0
    assert origin(mk(k_bid=setp("k_bid", 40, .481), k_ask=setp("k_ask", 40, .519))).pull == 0  # 1.8c
    half = origin(mk(k_bid_sz=setp("k_bid_sz", 40, 50.)))  # exactly 50%
    assert half.pull == 1 and half.pull_side == -1 and half.cls223 == 0 and half.bid_fall
    assert origin(mk(k_bid_sz=setp("k_bid_sz", 40, 50.01))).pull == 0
    ask = origin(mk(k_ask_sz=setp("k_ask_sz", 40, 10.)))
    assert ask.pull == 1 and ask.pull_side == 1
    both = origin(mk(k_ask_sz=setp("k_ask_sz", 40, 10.), k_bid_sz=setp("k_bid_sz", 40, 10.)))
    assert both.pull == 1 and both.pull_side == 0
    # a size fall with a changed touch price is not a pull (bid and ask both move one tick down: widening 0, mid moves 1c -> a CH222 unit anyway)
    ch = origin(mk(k_bid=setp("k_bid", 40, .48), k_ask=setp("k_ask", 40, .50), k_bid_sz=setp("k_bid_sz", 40, 10.), k_ask_sz=setp("k_ask_sz", 40, 10.)))
    assert ch.pull == 0 and ch.cls223 == 4
    z = origin(mk(k_bid_sz=_chain(setp("k_bid_sz", 35, 0.), setp("k_bid_sz", 40, 0.))))  # size 0 at s0: that side's condition is false, counted size_zero
    assert z.size_zero and z.pull == 0
    assert origin(mk()).moh == (T0 + 4800) % 3600


# --- CH222 -------------------------------------------------------------------------------------------------------------------------


def test_ch222_threshold_and_classes():
    just = origin(mk(k_bid=setp("k_bid", 40, .4949), k_ask=setp("k_ask", 40, .5149)))  # 0.49c: below the 0.5c edge
    assert just.cls222 == 3 and just.cls223 == 3
    edge = origin(mk(k_bid=setp("k_bid", 40, .495), k_ask=setp("k_ask", 40, .515)))  # exactly 0.5c
    assert edge.cls222 == 1 and edge.abs_dk1 == pytest.approx(.005) and edge.sign == 1
    mvk = dict(k_bid=setp("k_bid", 40, .495), k_ask=setp("k_ask", 40, .515))
    tr = origin(mk(**mvk, k_last=_chain(setp("k_last", 38, .51), setp("k_last", 39, .51), setp("k_last", 40, .51))))
    assert tr.cls222 == 0 and tr.traded == 1 and tr.trade_steps == 1
    amb = origin(mk(**mvk, k_vol24=_chain(setp("k_vol24", 39, 1100.), setp("k_vol24", 40, 1100.))))
    assert amb.cls222 == 2
    two = origin(mk(**mvk, k_last=_chain(setp("k_last", 37, .51), setp("k_last", 38, .51), setp("k_last", 39, .52), setp("k_last", 40, .52))))
    assert two.trade_steps == 2
    down = origin(mk(k_bid=setp("k_bid", 40, .485), k_ask=setp("k_ask", 40, .505)))
    assert down.sign == -1
    pop = pd.DataFrame([edge, tr, amb, down])
    assert len(lt.population(pop, "CH222")) == 3  # ambiguous excluded
    X = lt.add_test_columns(pop, None, {"rv60_P": {"centre": .01, "scale": .005}, "rv60_K": {"centre": .01, "scale": .005}})
    assert X["s_r1"].iloc[3] == -pop["r1"].iloc[3] and X["s_gap"].iloc[0] == pop["gap"].iloc[0]


def test_ch222_two_day_block_strata():
    anchor = lt._day_epoch("20261110")
    t = np.array([anchor, anchor + 86400, anchor + 2 * 86400, anchor + 4 * 86400 - 1, anchor + 4 * 86400])
    assert list(((t - anchor) // (2 * lt.DAY_S)).astype(int)) == [0, 0, 1, 1, 2]


def test_disjoint_222_223_property():
    rng = np.random.default_rng(7)
    n = 400
    for _ in range(12):
        step = rng.choice([0, 0, 0, .0004, .01, -.01], n) * (rng.random(n) < 0.3)
        kb = np.round(0.5 + np.cumsum(step) % 0.2, 4)
        pad = np.full(10, kb[-1])
        cols = mk(n=n + 10, k_bid=np.concatenate([kb, pad]) - .01, k_ask=np.concatenate([kb, pad]) + .01, k_last=np.round(rng.random(n + 10), 2),
                  k_vol24=1000 + np.cumsum(rng.random(n + 10) < 0.1) * 50.)
        A = lt.to_grid(cols, ["K|1"], T0, n + 10)
        js = np.arange(35, n, 5)
        df = lt.build_origins(A, T0, js, _meta(K=len(js)), check_e009=True)
        u = df[df.status == lt.ST["unit"]]
        assert len(u) > 10
        assert not ((u.cls222 < 3) & (u.cls223 == 0)).any()  # no origin is both a CH222 and a CH223 unit
        assert not ((u.cls222 == 3) & (u.cls223 == 4)).any()


# --- the event-phase gate ----------------------------------------------------------------------------------------------------------


def test_phase_offset_rounding():
    for n_g in (144, 288):
        s = max(4, math.ceil(n_g / 4))
        for n_p in (4, 5, 36, 100, n_g):
            for o in (s, n_g // 2, n_g - s):
                assert 1 <= lt.phase_offset(o, n_p, n_g) <= n_p - 1
    assert lt.phase_offset(36, 4, 144) == 1 and lt.phase_offset(108, 4, 144) == 3 and lt.phase_offset(72, 50, 144) == 25


def test_event_phase_plan_exclusions_and_common_shift():
    n_g = 144
    ev = np.array(["e1"] * 24 + ["e2"] * 6 + ["e3"] * 8)
    pair = np.array(["a"] * 12 + ["b"] * 12 + ["c"] * 3 + ["d"] * 3 + ["f"] * 4 + ["g"] * 4)
    order = np.concatenate([np.arange(12), np.arange(12), np.arange(3), np.arange(3), np.arange(4), np.arange(4)]).astype(float)
    pl = lt.event_phase_plan(ev, pair, order)
    assert len(pl["plan"]) == 1 and pl["excluded_strata"] == 2 and pl["excluded_pairs"] == 2  # e2: pairs < 4 units; e3: 8 rows < 16
    # a complete stratum (units fill every slot) is shifted by one common time offset
    pair2 = np.array(["a"] * n_g + ["b"] * n_g)
    ord2 = np.concatenate([np.arange(n_g), np.arange(n_g)]).astype(float)
    pl2 = lt.event_phase_plan(np.array(["e"] * (2 * n_g)), pair2, ord2)
    e = np.random.default_rng(1).normal(size=2 * n_g)
    ep, offs = lt.event_phase_shift(e, pl2["plan"], n_g, np.random.default_rng(9))
    o = offs[0]
    assert 36 <= o <= 108 and len(offs) == 1
    for p in (slice(0, n_g), slice(n_g, 2 * n_g)):
        assert np.allclose(ep[p], np.roll(e[p], o))  # residual of pair p at slot j equals the original at slot j - o (mod n_g)
    # one offset per stratum and draw, shared by every pair of the event
    ev3 = np.array(["x"] * 32 + ["y"] * 32)
    pair3 = np.array(["a"] * 16 + ["b"] * 16 + ["c"] * 16 + ["d"] * 16)
    pl3 = lt.event_phase_plan(ev3, pair3, np.tile(np.arange(16), 4).astype(float))
    _, offs3 = lt.event_phase_shift(np.arange(64.), pl3["plan"], n_g, np.random.default_rng(2))
    assert len(offs3) == 2


def test_event_phase_gate_runs_and_is_deterministic():
    rng = np.random.default_rng(4)
    rows = [{"pid": f"e{e}p{p}", "ev": f"E{e}", "t": float(t * 600), "day": "d0", "x": rng.normal(), "c": rng.normal()} for e in range(6) for p in range(2) for t in range(60)]
    df = pd.DataFrame(rows)
    y = df.c.to_numpy() * 0.5 + rng.normal(size=len(df))
    a = lt.event_phase_fl_gate(df, y, "x", ["c"], stratum="day", n_g=144, draws=40, seed=20261391)
    b2 = lt.event_phase_fl_gate(df, y, "x", ["c"], stratum="day", n_g=144, draws=40, seed=20261391)
    assert a["testable"] and a == b2 and a["share_rows_shifted"] > 0.9
    assert not lt.event_phase_fl_gate(df.iloc[:5], y[:5], "x", ["c"], stratum="day", n_g=144, draws=10, seed=1)["testable"]


# --- paths, counts-only, shared machinery ---------------------------------------------------------------------------------------------


def test_path_allow_list(tmp_path):
    ok = tmp_path / "data-dumps" / "research_lab" / "xv_quotes" / "quotes" / "20261110.jsonl"
    assert lt.check_path(ok) == ok
    for bad in ("data-dumps/research_lab/cross_venue_live/predictions.jsonl", "data-dumps/research_lab/cross_venue_live/outcomes_20261022.jsonl",
                "data-dumps/research_lab/cross_venue_live/quotes/20261020.jsonl.bak", "data-dumps/research_lab/arepo_val/x.json",
                "data-dumps/research_lab/live_tests9/x.csv", "data-dumps/research_lab/cross_venue/quotes/20261020.jsonl", "data-dumps/signal_engine/x",
                "data-dumps/research_lab/trade_sample/x", "data-dumps/research_lab/xv_quotes/predictions.jsonl", "/etc/passwd"):
        with pytest.raises(lt.Refused):
            lt.check_path(tmp_path / bad)


def _write_runs(xv, t_from, t_to, n_pairs=6, R="2026-11-09T20:00:00Z", mode="w", load_first=True):
    with (xv / "runs.jsonl").open(mode) as fh:
        for t in range(t_from, t_to, 120):
            fh.write(json.dumps({"kind": "cycle", "t": t, "pairs_loaded_utc": R, "load": load_first and mode == "w" and t == t_from, "pairs": n_pairs, "src": "xv_quotes_v1"}) + "\n")


def _window_tree(tmp, *, hours=8, seed=2, n_pairs=6, runs_until=None):
    xv = tmp / "data-dumps" / "research_lab" / "xv_quotes"
    (xv / "quotes").mkdir(parents=True)
    (xv / "pairs").mkdir()
    snap = tmp / "data-dumps" / "research_lab" / "snapshots"
    rng = np.random.default_rng(seed)
    pids = [f"K{i}|{i}" for i in range(n_pairs)]
    t0 = int(lt.epoch("2026-11-10T00:00:00Z"))
    t1 = t0 + hours * 3600
    q = _synth_quotes(rng, pids, t0, t1, src="xv_quotes_v1")
    for d, ls in q.items():
        (xv / "quotes" / f"{d}.jsonl").write_text("".join(json.dumps(x) + "\n" for x in ls))
    R = "2026-11-09T20:00:00Z"
    doc = {"refreshed_utc": R, "version": "x", "pairs": [{"pid": p, "p_event_id": f"E{i // 2}", "p_market_id": str(i), "k_ticker": f"K{i}", "token0": f"t{i}",
                                                          "hand_verified": False, "fee_rate": 0.02, "p_end": "2026-12-30T00:00:00Z", "k_close": "2026-12-30T00:00:00Z"}
                                                         for i, p in enumerate(pids)]}
    (xv / "pairs" / "pairs_20261109T200000Z.json").write_text(json.dumps(doc))
    _write_runs(xv, t0, t1 if runs_until is None else runs_until, n_pairs, R)
    cid = "20261109T120000Z"
    (snap / cid).mkdir(parents=True)
    pd.DataFrame({"market_id": [str(i) for i in range(n_pairs)], "condition_id": [f"c{i}" for i in range(n_pairs)], "fee_type": ["x"] * n_pairs,
                  "fee_category": ["politics"] * n_pairs, "series_slugs": [""] * n_pairs}).to_csv(snap / cid / "rows_ext.csv.gz", index=False)
    (snap / cid / "manifest.json").write_text(json.dumps({"state": "complete", "finished_utc": "2026-11-09T12:30:00Z"}))
    feed = tmp / "data-dumps" / "research_lab" / "reward_params"
    (feed / "20261109T130000Z").mkdir(parents=True)
    with gzip.open(feed / "20261109T130000Z" / "rows.jsonl.gz", "wt") as fh:
        fh.write(json.dumps({"condition_id": "c0", "rewards_config": [{"rate_per_day": 5.0}, {"rate_per_day": 0.0}, {"rate_per_day": 2.5}]}) + "\n")
        fh.write(json.dumps({"condition_id": "c1", "rewards_config": []}) + "\n")
    (feed / "20261109T130000Z" / "manifest.json").write_text(json.dumps({"state": "complete", "finished_utc": "2026-11-09T13:20:00Z"}))
    (feed / "20261109T190000Z").mkdir()
    (feed / "20261109T190000Z" / "manifest.json").write_text(json.dumps({"state": "failed", "finished_utc": "2026-11-09T19:20:00Z"}))
    return xv, snap, t0, t1


def _synth_quotes(rng, pids, t_start, t_end, *, src=None, tick=0.01, trade_p=0.04):
    ts = np.arange(t_start, t_end, 120)
    n = len(ts)
    out: dict[str, list] = {}
    for pid in pids:
        x = np.clip(0.5 + np.cumsum(rng.normal(0, 0.0015, n)), 0.08, 0.92)
        km = np.round((x + rng.normal(0, 0.002, n)) / 0.01) * 0.01
        lag = np.concatenate([[km[0]] * 2, km[:-2]])
        pm = np.round(lag / 0.01) * 0.01
        ksp = 0.01 * (2 + (rng.random(n) < 0.35) + (rng.random(n) < 0.15))
        psp = 0.01 * (1 + (rng.random(n) < 0.5))
        sz = np.exp(rng.normal(5, 0.5, (4, n))).round(0)
        trade = rng.random(n) < trade_p
        last, vol = km[0], 1000.0
        for i in range(n):
            if trade[i]:
                last = km[i] + (0.01 if rng.random() < 0.5 else -0.01) * (ksp[i] > 0.015)
                vol += 50
            t = int(ts[i])
            ln = {"t": t, "pid": pid, "k_bid": round(km[i] - ksp[i] / 2, 4), "k_ask": round(km[i] + ksp[i] / 2, 4), "k_last": round(last, 4), "k_bid_sz": sz[0, i],
                  "k_ask_sz": sz[1, i], "k_status": "active", "k_vol24": vol, "k_recv": t + 1.5, "p_bid": round(pm[i] - psp[i] / 2, 4), "p_ask": round(pm[i] + psp[i] / 2, 4),
                  "p_bid_sz": sz[2, i], "p_ask_sz": sz[3, i], "p_last": round(pm[i], 4), "p_book_ts": float(t - 5 - (i % 3)), "p_tick": tick, "p_min_size": 5.0, "p_recv": t + 2.0}
            ln["k_mid"] = round((ln["k_bid"] + ln["k_ask"]) / 2, 6)
            ln["p_mid"] = round((ln["p_bid"] + ln["p_ask"]) / 2, 6)
            if src:
                ln["src"] = src
            out.setdefault(datetime.fromtimestamp(t, UTC).strftime("%Y%m%d"), []).append(ln)
    for d in out:
        out[d].sort(key=lambda r: (r["t"], r["pid"]))
    return out


def _tree_files(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file() and p.name not in ("run.lock", "runs.jsonl", "pairs_seen.jsonl")}


def test_reward_feed_join_and_fee_rate_in_frozen_lines(tmp_path):
    xv, snap, t0, t1 = _window_tree(tmp_path, hours=4, runs_until=None)
    feed = tmp_path / "data-dumps" / "research_lab" / "reward_params"
    out = tmp_path / "data-dumps" / "research_lab" / "live_tests10"
    _write_runs(xv, t0, t0 + 2 * 3600 + 32 * 60)
    lt.run_once(xv_root=xv, out_root=out, snapshot_roots=[snap], spec=lt.load_spec(sha=None), now=float(t0 + 2 * 3600 + 32 * 60), feed_roots=[feed])
    fr = pd.read_csv(out / "hedge" / "frozen" / "20261110" / "0220.csv.gz")
    by = fr.set_index("pid")
    assert by.loc["K0|0", "rewarded"] == 1 and by.loc["K0|0", "reward_rate"] == pytest.approx(7.5)
    assert by.loc["K1|1", "rewarded"] == 1 and by.loc["K1|1", "reward_rate"] == 0.0 and by.loc["K2|2", "rewarded"] == 0 and np.isnan(by.loc["K2|2", "reward_rate"])
    assert set(fr.fee_rate) == {0.02}
    # a failed capture is never used; no feed gives NaN flags
    assert lt.feed_listing([feed], lt.epoch("2026-11-09T19:30:00Z"))["capture"] == "20261109T130000Z"
    assert lt.feed_listing([feed], lt.epoch("2026-11-09T13:00:00Z")) is None


def test_reader_run_once_outputs_and_write_once(tmp_path):
    xv, snap, t0, t1 = _window_tree(tmp_path, hours=8, runs_until=None)
    out = tmp_path / "data-dumps" / "research_lab" / "live_tests10"
    spec = lt.load_spec(sha=None)
    # real-time simulation: run 1 sees the cycles up to 02:32, run 2 those up to 03:50
    _write_runs(xv, t0, t0 + 2 * 3600 + 32 * 60)
    n1 = lt.run_once(xv_root=xv, out_root=out, snapshot_roots=[snap], spec=spec, now=float(t0 + 2 * 3600 + 32 * 60))
    assert n1["exit"] == 0 and n1["origins"] > 10
    # origins before reg + 3,840 s are counted lt10_boundary; nothing is a unit there
    s0 = pd.read_csv(out / "status" / "20261110" / "0100.csv.gz")
    assert set(s0.status) == {"lt10_boundary"} and set(s0.role) == {"prospective_unregistered"}
    s1 = pd.read_csv(out / "status" / "20261110" / "0200.csv.gz")
    assert "unit" in set(s1.status) and len(s1) == 6
    # the origin 02:20 is frozen on time (written before t + 1,080 s), the origin 02:00 is late
    assert (out / "hedge" / "frozen" / "20261110" / "0220.csv.gz").exists() and (out / "hedge" / "frozen" / "20261110" / "0200.late.csv.gz").exists()
    assert not list(out.glob("*/outcomes/*/*0220*"))  # no target before its endpoint cycle exists
    _write_runs(xv, t0 + 2 * 3600 + 32 * 60, t0 + 3 * 3600 + 50 * 60, mode="a")
    n2 = lt.run_once(xv_root=xv, out_root=out, snapshot_roots=[snap], spec=spec, now=float(t0 + 3 * 3600 + 50 * 60))
    assert n2["exit"] == 0
    oc = pd.read_csv(out / "hedge" / "outcomes" / "20261110" / "0220.h20.csv.gz")
    assert set(oc.tg_status) <= set(lt.TG_NAMES.values()) and oc.loc[oc.tg_status != "two_sided", "pmid_h"].isna().all() and (oc.tg_status == "two_sided").any()
    assert (out / "hedge" / "outcomes" / "20261110" / "0220.h10.csv.gz").exists() and list(out.glob("traded/outcomes/*/*.h20.csv.gz"))
    assert not (out / "hedge" / "outcomes" / "20261110" / "0220.h60.csv.gz").exists()  # only CH222 has the +60 min horizon
    tw = pd.read_csv(out / "hedge" / "twins" / "20261110" / "0220.csv.gz")
    assert {"tw_ok", "dsK_tw", "pull_tw", "traded_tw"} <= set(tw.columns)
    fr = pd.read_csv(out / "hedge" / "frozen" / "20261110" / "0220.csv.gz")
    assert {"dsK", "sK_s0", "pull", "cls223", "cls222", "written_utc", "role", "spec_sha", "code_sha", "in_scope"} <= set(fr.columns)
    # no CH222 +60 min target before the cycle t + 3,720 s: origin 03:00's h60 file would need the cycle at 04:02
    assert not list(out.glob("traded/outcomes/*/03[0-9][0-9].h60.csv.gz"))
    # a second run with nothing new writes nothing and touches nothing
    before = _tree_files(out)
    assert lt.run_once(xv_root=xv, out_root=out, snapshot_roots=[snap], spec=spec, now=float(t0 + 3 * 3600 + 51 * 60))["exit"] == lt.TEMPFAIL
    assert _tree_files(out) == before
    # later still: the +60 min target appears
    _write_runs(xv, t0 + 3 * 3600 + 50 * 60, t0 + 4 * 3600 + 10 * 60, mode="a")
    lt.run_once(xv_root=xv, out_root=out, snapshot_roots=[snap], spec=spec, now=float(t0 + 4 * 3600 + 10 * 60))
    assert list(out.glob("traded/outcomes/*/*.h60.csv.gz"))
    # write-once: the earlier target is byte-identical
    assert _tree_files(out)["hedge/outcomes/20261110/0220.h20.csv.gz"] == before["hedge/outcomes/20261110/0220.h20.csv.gz"]


def test_reader_waits_for_the_cycle_line_and_skips_incomplete_lines(tmp_path):
    xv, snap, t0, t1 = _window_tree(tmp_path, hours=4)
    out = tmp_path / "data-dumps" / "research_lab" / "live_tests10"
    runs = (xv / "runs.jsonl").read_text().splitlines()
    cut = int(lt.epoch("2026-11-10T02:00:00Z"))
    keep = [x for x in runs if json.loads(x)["t"] <= cut]
    (xv / "runs.jsonl").write_text("\n".join(keep) + "\n" + '{"kind":"cycle","t":' + str(cut + 120))  # an incomplete trailing line
    lt.run_once(xv_root=xv, out_root=out, snapshot_roots=[snap], spec=lt.load_spec(sha=None), now=float(t0 + 3 * 3600))
    done = sorted(p.parent.name + p.name[:4] for p in (out / "status").rglob("*.csv.gz"))
    assert done and max(done) <= "202611100200"  # no origin beyond the last complete runs.jsonl line


def test_run_lock_is_internal_and_non_blocking(tmp_path):
    import fcntl

    xv, snap, t0, t1 = _window_tree(tmp_path, hours=3)
    out = tmp_path / "data-dumps" / "research_lab" / "live_tests10"
    out.mkdir(parents=True)
    fh = open(out / "run.lock", "w")  # noqa: SIM115
    fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    res = lt.run_once(xv_root=xv, out_root=out, snapshot_roots=[snap], spec=lt.load_spec(sha=None), now=float(t0 + 9000))
    fh.close()
    assert res == {"status": "locked", "exit": lt.TEMPFAIL}


def test_reader_store_limit(tmp_path):
    xv, snap, t0, t1 = _window_tree(tmp_path, hours=3)
    out = tmp_path / "data-dumps" / "research_lab" / "live_tests10"
    spec = copy.deepcopy(lt.load_spec(sha=None))
    spec["reader"]["max_store_bytes"] = 10
    out.mkdir(parents=True)
    (out / "junk.bin").write_bytes(b"x" * 100)
    assert lt.run_once(xv_root=xv, out_root=out, snapshot_roots=[snap], spec=spec, now=float(t0 + 9000))["exit"] == 3


def test_causality_later_quote_lines_leave_frozen_lines_identical(tmp_path):
    outs = []
    cut = int(lt.epoch("2026-11-10T03:00:00Z"))
    for k, mutate in enumerate((False, True)):
        d = tmp_path / f"t{k}"
        xv, snap, t0, t1 = _window_tree(d, hours=6)
        out = d / "data-dumps" / "research_lab" / "live_tests10"
        if mutate:
            f = xv / "quotes" / "20261110.jsonl"
            new = []
            for raw in f.read_text().splitlines():
                ln = json.loads(raw)
                if ln["t"] > cut:
                    for key in ("k_bid", "k_ask", "p_bid", "p_ask", "k_last", "p_bid_sz", "k_bid_sz"):
                        ln[key] = round(ln[key] * 0.37 + 0.011, 4)
                new.append(json.dumps(ln))
            f.write_text("\n".join(new) + "\n")
        lt.run_once(xv_root=xv, out_root=out, snapshot_roots=[snap], spec=lt.load_spec(sha=None), now=float(t0 + 6 * 3600 + 100))
        outs.append(out)
    a, b2 = _tree_files(outs[0]), _tree_files(outs[1])
    checked = 0
    for name in a:
        m = re.match(r"(status|hedge/frozen|flinch/frozen|traded/frozen)/(\d{8})/(\d{4})(\.late)?\.csv\.gz$", name)
        if not m:
            continue
        t = lt._day_epoch(m.group(2)) + int(m.group(3)[:2]) * 3600 + int(m.group(3)[2:]) * 60
        if t <= cut:
            assert gzip.decompress(a[name]) == gzip.decompress(b2[name]), name  # a frozen origin never reads a later poll
            checked += 1
    assert checked > 20


def test_ops_stats_reads_no_price_column(tmp_path):
    xv, snap, t0, t1 = _window_tree(tmp_path, hours=5)
    out = tmp_path / "data-dumps" / "research_lab" / "live_tests10"
    lt.run_once(xv_root=xv, out_root=out, snapshot_roots=[snap], spec=lt.load_spec(sha=None), now=float(t0 + 5 * 3600))
    assert set(lt.OPS_COLS) == {"pid", "t", "status", "cls223", "cls222", "role", "in_scope"}
    res = lt.ops_stats(out)
    assert res["files"]["status"] > 10 and "unit" in res["status"]
    blob = json.dumps(res)
    assert "dsK" not in blob and "k_bid" not in blob
    df = lt._read_ops(next((out / "hedge" / "frozen").rglob("*.csv.gz")))
    assert set(df.columns) <= set(lt.OPS_COLS)
    s = lt.ops_stats_stream(xv)
    day = next(iter(s))
    assert s[day]["cycles"] > 0 and set(s[day]["presence"]) == {"k_last", "k_bid_sz", "k_ask_sz", "k_vol24", "k_recv", "p_bid_sz", "p_ask_sz", "p_recv"}
    pv = lt.presence_view(json.dumps({"t": 1, "pid": "a", "k_mid": .5, "p_mid": .5, "k_bid": .123, "k_recv": 3}).encode())
    assert "k_bid" not in pv and pv["has_k_mid"] is True and pv["k_lag"] == 2.0


# --- the seal and the censuses -----------------------------------------------------------------------------------------------------------


def _census_tree(tmp, *, n_pairs=12, trade_p=0.10):
    e9 = tmp / "data-dumps" / "research_lab" / "cross_venue_live"
    (e9 / "quotes").mkdir(parents=True)
    (e9 / "pairs").mkdir()
    snap = tmp / "data-dumps" / "research_lab" / "snapshots"
    rng = np.random.default_rng(1)
    pids = [f"K{i}|{i}" for i in range(n_pairs)]
    t0 = int(lt.epoch("2026-10-20T00:00:00Z"))
    t1 = int(lt.epoch("2026-10-24T01:00:00Z"))
    q = _synth_quotes(rng, pids, t0, t1, trade_p=trade_p)
    for d, ls in q.items():
        with gzip.open(e9 / "quotes" / f"{d}.jsonl.gz", "wt") as fh:
            fh.writelines(json.dumps(x) + "\n" for x in ls)
    doc = {"refreshed_utc": "2026-10-19T00:00:00Z", "version": "x", "pairs": [
        {"pid": p, "p_event_id": f"E{i // 2}", "p_market_id": str(i), "k_ticker": f"K{i}", "token0": f"t{i}", "hand_verified": i % 3 == 0, "fee_rate": 0.02,
         "p_end": "2026-12-30T00:00:00Z", "k_close": "2026-12-30T00:00:00Z"} for i, p in enumerate(pids)]}
    (e9 / "pairs" / "pairs_20261019T000000Z.json").write_text(json.dumps(doc))
    (e9 / "refresh.log").write_text(json.dumps({"refreshed_utc": "2026-10-19T00:00:00Z", "k_requests": 100, "p_requests": 500}) + "\n")
    for d in ("20261020", "20261021", "20261022"):
        cid = f"{d}T000000Z"
        (snap / cid).mkdir(parents=True)
        pd.DataFrame({"market_id": [str(i) for i in range(n_pairs)], "fee_type": ["x"] * n_pairs, "fee_category": ["politics"] * n_pairs,
                      "series_slugs": [""] * n_pairs}).to_csv(snap / cid / "rows_ext.csv.gz", index=False)
        (snap / cid / "manifest.json").write_text(json.dumps({"state": "complete", "finished_utc": f"{d[:4]}-{d[4:6]}-{d[6:]}T00:30:00Z"}))
    spec = copy.deepcopy(lt.load_spec(sha=None))
    spec["census_inputs"] = {"span": {"start_utc": "2026-10-21T00:00:00Z", "end_utc": "2026-10-24T00:00:00Z"},
                             "quote_days": ["20261020", "20261021", "20261022", "20261023", "20261024"], "pair_refresh_window": ["2026-10-19T00:00:00Z", "2026-10-24T00:00:00Z"]}
    g = spec["census_gates"]
    g["CF10"].update(min_covered_days=2.5, min_pairs=5, min_events=3, min_g_eff=3)
    for v in g["CK10"].values():
        for k in list(v):
            if k.startswith("min_projected"):
                v[k] = 10
            if k == "min_pairs":
                v[k] = 2
            if k == "pair_min_units":
                v[k] = 100
            if k == "min_withdrawals_per_pair":
                v[k] = 3
            if k == "min_moves_per_pair":
                v[k] = 5
            if k == "min_r_pairs":
                v[k] = 2
    g["CK10"]["CH223"]["withdrawal_share_range"] = [0.01, 0.5]
    g["CK10"]["CH222"]["traded_share_range"] = [0.05, 0.95]
    for v in g["CD10"].values():
        v["min_g_eff"] = 3
    return e9, snap, spec


def _seal(tmp, e9, snap, spec, **kw):
    seal = lt.seal_inputs(e009_roots=[e9], snapshot_roots=[snap], spec=spec, e009_commit=kw.get("e9c", "abcdef1"), e010_commit=kw.get("e10c", "abcdef2"),
                          git=kw.get("git", lambda r, *a: "deadbeef"), scope_decision=kw.get("scope_decision"))
    if "error" not in seal:
        sp = tmp / f"seal_{len(list(tmp.glob('seal_*.json')))}.json"
        sp.write_text(json.dumps(seal, default=str))
        seal["_path"] = sp
    return seal


@pytest.fixture(scope="module")
def census_world(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("census")
    e9, snap, spec = _census_tree(tmp)
    seal = _seal(tmp, e9, snap, spec)
    cf = lt.census_family(seal=seal["_path"], e009_roots=[e9], snapshot_roots=[snap], spec=spec)
    ck = lt.census_kalshi(seal=seal["_path"], e009_roots=[e9], snapshot_roots=[snap], spec=spec, cf10=cf)
    cd = lt.census_design(seal=seal["_path"], e009_roots=[e9], snapshot_roots=[snap], spec=spec, cf10=cf, ck10=ck)
    return {"tmp": tmp, "e9": e9, "snap": snap, "spec": spec, "seal": seal, "cf": cf, "ck": ck, "cd": cd}


def test_seal_refuses_without_both_commits(tmp_path):
    e9, snap, spec = _census_tree(tmp_path)
    assert "analysis commit" in _seal(tmp_path, e9, snap, spec, e9c=None)["error"]
    assert "analysis commit" in _seal(tmp_path, e9, snap, spec, e10c="zz")["error"]
    assert "does not resolve" in _seal(tmp_path, e9, snap, spec, git=lambda r, *a: None)["error"]
    s = _seal(tmp_path, e9, snap, spec)
    assert s["n_missing"] == {"quotes": 0, "sidecars": 0, "refresh_log": 0} and s["scope"] == "non_sports_ex_crypto" and s["n_files"] == 13
    assert s["e009_analysis_commit"] == "deadbeef" and s["design_text_sha256"] == lt.DESIGN_TEXT_SHA256


def test_seal_scope_rules(tmp_path):
    e9, snap, spec = _census_tree(tmp_path)
    sp = copy.deepcopy(spec)
    sp["scope"] = "ex_crypto"
    assert "owner decision" in _seal(tmp_path, e9, snap, sp)["error"]
    assert _seal(tmp_path, e9, snap, sp, scope_decision="ledger line 2026-10-30")["scope"] == "ex_crypto"
    sp["scope"] = "all"
    assert "not in" in _seal(tmp_path, e9, snap, sp)["error"]


def test_seal_refuses_a_different_design_text(tmp_path):
    e9, snap, spec = _census_tree(tmp_path)
    other = tmp_path / "other.md"
    other.write_text("not the frozen design")
    res = lt.seal_inputs(e009_roots=[e9], snapshot_roots=[snap], spec=spec, e009_commit="abcdef1", e010_commit="abcdef2", design_path=other, git=lambda r, *a: "d")
    assert "differs from the text-frozen" in res["error"]


def test_census_refusals(census_world):
    import shutil

    w = census_world
    sp = w["seal"]["_path"]
    bad = copy.deepcopy(w["spec"])
    bad["scope"] = "ex_crypto"
    assert "scope" in lt.census_family(seal=sp, e009_roots=[w["e9"]], snapshot_roots=[w["snap"]], spec=bad)["error"]
    bad2 = copy.deepcopy(w["spec"])
    bad2["census_gates"]["CF10"]["min_pairs"] = 1
    assert "census blocks differ" in lt.census_family(seal=sp, e009_roots=[w["e9"]], snapshot_roots=[w["snap"]], spec=bad2)["error"]
    # tampering: a sealed file with different bytes is refused
    tamper = w["tmp"] / "t2" / "data-dumps" / "research_lab"
    shutil.copytree(w["e9"], tamper / "cross_venue_live")
    f = next((tamper / "cross_venue_live" / "quotes").glob("20261022*"))
    with gzip.open(f, "wt") as fh:
        fh.write("{}\n")
    r2 = lt.census_family(seal=sp, e009_roots=[tamper / "cross_venue_live"], snapshot_roots=[w["snap"]], spec=w["spec"])
    assert "input identity" in r2["error"] and r2["n_bad"] >= 1
    # a sealed file absent from every root is refused too
    miss = w["tmp"] / "t3" / "data-dumps" / "research_lab"
    shutil.copytree(w["e9"], miss / "cross_venue_live")
    next((miss / "cross_venue_live" / "quotes").glob("20261021*")).rename(w["tmp"] / "moved.gz")
    assert "input identity" in lt.census_family(seal=sp, e009_roots=[miss / "cross_venue_live"], snapshot_roots=[w["snap"]], spec=w["spec"])["error"]
    # a seal against a different design text
    sd = json.loads(sp.read_text())
    sd["design_text_sha256"] = "0" * 64
    p2 = w["tmp"] / "seal_bad.json"
    p2.write_text(json.dumps(sd))
    assert "different LIVE_TESTS_10.md" in lt.census_family(seal=p2, e009_roots=[w["e9"]], snapshot_roots=[w["snap"]], spec=w["spec"])["error"]


def test_census_family_counts_and_stage_order(census_world):
    cf, ck, cd = census_world["cf"], census_world["ck"], census_world["cd"]
    assert cf["counts_only"] and cf["gates"]["pass"] and cf["counts"]["eligible_origins"] == 12 * 144 * 3 and cf["covered_days"] == pytest.approx(3.0)
    assert cf["counts"]["pairs"] == 12 and cf["counts"]["events"] == 6 and cf["counts"]["g_eff"] == pytest.approx(6.0)
    assert cf["descriptive"]["records"][0]["l_obs_reason"].startswith("look-back")
    assert cf["descriptive"]["refresh_duration"]["rows"][0]["duration_lower_bound_s"] == pytest.approx(1200.0)
    assert ck["alive"] and set(ck["tests"]) == {"CH224", "CH223", "CH222"}
    assert cd["k_tests"] and set(cd["k_tests"]) <= set(cd["tests"]) and cd["census_fixed"]["scale_K_cents"] > 0
    w = census_world
    assert "CF10 did not pass" in lt.census_kalshi(seal=w["seal"]["_path"], e009_roots=[w["e9"]], snapshot_roots=[w["snap"]], spec=w["spec"], cf10={"gates": {"pass": False}})["error"]
    assert "no test survived" in lt.census_design(seal=w["seal"]["_path"], e009_roots=[w["e9"]], snapshot_roots=[w["snap"]], spec=w["spec"], cf10=cf, ck10={"alive": []})["error"]


def test_census_gate_failures_drop_tests(census_world):
    w = census_world
    s = copy.deepcopy(w["spec"])
    s["census_gates"]["CF10"]["min_covered_days"] = 3.5  # below the minimum covered days: every gate NaN-fails
    seal = _seal(w["tmp"], w["e9"], w["snap"], s)
    r = lt.census_family(seal=seal["_path"], e009_roots=[w["e9"]], snapshot_roots=[w["snap"]], spec=s)
    assert not r["gates"]["pass"] and r["gates"].get("values_nan") and r["alive"] == []
    s2 = copy.deepcopy(w["spec"])
    s2["census_gates"]["CF10"]["min_pairs"] = 60
    seal2 = _seal(w["tmp"], w["e9"], w["snap"], s2)
    r2 = lt.census_family(seal=seal2["_path"], e009_roots=[w["e9"]], snapshot_roots=[w["snap"]], spec=s2)
    assert not r2["gates"]["pass"] and not r2["gates"]["pairs_ok"]


def test_census_origin_side_only_later_polymarket_fields_change_nothing(tmp_path):
    """Altering every Polymarket field of polls later than the span's last origin leaves every census output unchanged (7: the census reads no
    Polymarket field of a poll later than the last origin)."""
    outs = []
    for k in (0, 1):
        d = tmp_path / f"c{k}"
        e9, snap, spec = _census_tree(d, n_pairs=8)
        if k == 1:
            last = int(lt.epoch("2026-10-24T00:00:00Z")) - 600
            for f in sorted((e9 / "quotes").glob("*.gz")):
                lines = []
                with gzip.open(f, "rt") as fh:
                    for raw in fh:
                        ln = json.loads(raw)
                        if ln["t"] > last:
                            for key in ("p_bid", "p_ask", "p_bid_sz", "p_ask_sz", "p_book_ts", "p_recv"):
                                ln[key] = 999.0
                        lines.append(json.dumps(ln))
                with gzip.open(f, "wt") as fh:
                    fh.write("\n".join(lines) + "\n")
        seal = _seal(d, e9, snap, spec)
        outs.append(lt.census_family(seal=seal["_path"], e009_roots=[e9], snapshot_roots=[snap], spec=spec))
    a, b2 = outs
    for key in ("counts", "gates", "covered_days", "field_presence", "late_origin_share"):
        assert a[key] == b2[key], key


def test_field_presence_gate_kills_dependent_tests():
    spec = lt.load_spec(sha=None)
    pres = {"k_valid": 100, "p_valid": 100, "k_last": 90, "k_bid_sz": 100, "k_ask_sz": 100, "k_vol24": 0, "k_recv": 100, "p_bid_sz": 100, "p_ask_sz": 100, "p_recv": 100}
    fp = lt.field_presence(pres, spec)
    assert fp["dead_tests"] == ["CH222", "CH223"] and fp["shares"]["k_vol24"] == 0.0  # k_vol24 is printed only
    assert lt.field_presence(dict(pres, k_last=100, k_bid_sz=94), spec)["dead_tests"] == ["CH223"]
    assert lt.field_presence(dict(pres, k_last=100, p_recv=10), spec)["dead_tests"] == ["CH222", "CH223", "CH224"]


def test_event_concentration_excludes_top_event():
    rows = [{"pid": "a", "ev": "E1", "in_scope": True}] * 700 + [{"pid": f"b{i}", "ev": f"E{i % 5 + 2}", "in_scope": True} for i in range(300)]
    spec = copy.deepcopy(lt.load_spec(sha=None))
    spec["census_gates"]["CF10"].update(pair_min_eligible_origins=1, min_pairs=1, min_events=1, min_g_eff=1)
    r = lt.cf10_gates(pd.DataFrame(rows), {"unit": 1000}, 8.0, {"k_valid": 1, "p_valid": 1, **{f: 1 for f in lt.FIELD_DEPENDENCE}}, spec)
    assert r["exclude_event"] == "E1" and r["top_event_share"] == pytest.approx(0.7) and r["counts"]["events"] == 5


def test_kish_and_design_effect_gate():
    assert lt.g_eff(["a"] * 20 + ["b"] + ["c"]) == pytest.approx(22 ** 2 / (400 + 2))
    spec = lt.load_spec(sha=None)
    assert lt.de_gate10(["a", "b", "c", "d"], 1.0, spec)["DE_gate"] == 51.0  # the floor
    big = lt.de_gate10(["a"] * 1_000_000 + ["b"], 1.0, spec)
    assert big["DE_gate"] == pytest.approx(1 + (big["m_w"] - 1) * 0.0016667) and big["DE_gate"] > 51
    assert lt.overlap_factor(0.1) == pytest.approx(1.1) and lt.overlap_factor(-0.3) == 1.0


def test_mde_gate_formulas_use_max_of_declared_and_design():
    spec = lt.load_spec(sha=None)
    a = b.mde_common(spec)
    assert a["t_sum"] >= 3.47 and a["day_factor"] == 1.5
    # planning cells of sections 2-4 (VIF 1.5, DE 51, OF 1.1)
    assert lt.mde_declared("CH224", 123379.0, None, 51.0, 1.5, 1.1, spec) * 100 == pytest.approx(0.299, abs=0.004)
    assert lt.mde_declared("CH223", 2606.0, 105316.0, 51.0, 1.5, 1.1, spec) * 100 == pytest.approx(0.473, abs=0.01)
    assert lt.mde_declared("CH222", 4935.0, 6786.0, 51.0, 1.5, 1.1, spec) * 100 == pytest.approx(0.625, abs=0.01)
    assert lt.mde_declared("CH224", 1e5, None, 51.0, 1.5, float("nan"), spec) == float("inf")


def test_f_roles_are_fixed_by_design():
    spec = copy.deepcopy(lt.load_spec(sha=None))
    assert [lt.f_role(spec, t) for t in lt.TESTS] == ["binding", "label", "label"]
    s2 = copy.deepcopy(spec)
    s2["f_roles"]["CH223"] = "binding"
    with pytest.raises(RuntimeError):
        lt.f_role(s2, "CH223")
    s3 = copy.deepcopy(spec)
    s3["f_binding"] = True
    with pytest.raises(RuntimeError):
        lt.f_role(s3, "CH224")


def test_registration_rules():
    assert lt.registration_error("2026-11-03T01:00:00Z", "2026-11-03T02:00:00Z") is None
    assert "02:00" in lt.registration_error("2026-11-03T02:00:00Z", "2026-11-04T00:00:00Z")
    assert "T_E009" in lt.registration_error("2026-11-03T01:00:00Z", "2026-11-03T00:30:00Z")
    assert "staleness" in lt.registration_error("2026-11-03T01:00:00Z", "2026-11-03T02:00:00Z", "2026-12-01T00:00:00Z")
    assert "2026-11-10" in lt.registration_error("2026-11-03T01:00:00Z", "2026-11-03T02:00:00Z", "2026-11-09T00:00:00Z")


def test_load_spec_pin_rules(tmp_path):
    spec = json.loads(lt.SPEC_PATH.read_text())
    p = tmp_path / "s.json"
    p.write_text(json.dumps(spec))
    assert lt.load_spec(p, b.sha256_file(p))["_pinned"] is True
    with pytest.raises(RuntimeError, match="mismatch"):
        lt.load_spec(p, "0" * 64)
    bad = copy.deepcopy(spec)
    bad["mde_planning"]["CH223"]["sd"] = float("nan")
    p.write_text(json.dumps(bad))
    with pytest.raises(RuntimeError, match="NaN"):
        lt.load_spec(p, b.sha256_file(p))
    bad = copy.deepcopy(spec)
    bad["registered_utc"] = "2026-11-11T00:00:00Z"
    p.write_text(json.dumps(bad))
    with pytest.raises(RuntimeError, match="module constant"):
        lt.load_spec(p, None)
    bad = copy.deepcopy(spec)
    bad["design_text_sha256"] = "0" * 64
    p.write_text(json.dumps(bad))
    with pytest.raises(RuntimeError, match="design_text"):
        lt.load_spec(p, None)
    assert lt.design_text_sha() == lt.DESIGN_TEXT_SHA256 == spec["design_text_sha256"] and lt.design_text_error() is None


def test_spec_constants_match_the_design():
    spec = lt.load_spec(sha=None)
    assert spec["seeds"]["estimators"] == {"CH224": 20261301, "CH223": 20261302, "CH222": 20261303}
    assert spec["seeds"]["gates"] == {"CH224": 20261391, "CH223": 20261392, "CH222": 20261393} and spec["seeds"]["size_check"] == 20261397
    g = spec["census_gates"]
    assert g["CK10"]["CH224"]["min_projected_units"] == 31000 and g["CK10"]["CH223"]["min_projected_withdrawals"] == 2920
    assert g["CK10"]["CH222"]["min_projected_traded"] == 9650 and g["CF10"]["min_pairs"] == 60 and g["CF10"]["min_events"] == 30 and g["CF10"]["min_g_eff"] == 15
    assert g["CD10"]["CH224"]["max_mde_c"] == 1.0 and g["CD10"]["CH224"]["max_f_mde_c"] == 1.0 and g["CD10"]["CH223"]["max_mde_c"] == 0.5
    assert spec["pair_record_rule"]["L_s"] == 11400 and spec["reader"]["max_store_bytes"] == int(1.5 * 1024**3) and spec["reader"]["freeze_before_s"] == 1080
    assert lt.SPEC_SHA256 is None or lt.SPEC_SHA256 == b.sha256_file(lt.SPEC_PATH)


def test_code_sha256_map_normalises_the_pin_line(tmp_path):
    p = tmp_path / "m.py"
    p.write_text("A = 1\nSPEC_SHA256 = None\n")
    h1 = lt.code_sha256(p)
    p.write_text("A = 1\nSPEC_SHA256 = 'abc'\n")
    assert lt.code_sha256(p) == h1
    hs = lt.code_hashes()
    assert hs["live_tests10.py"] and hs["xv_quotes_poller.py"] and set(hs) == set(lt.CODE_FILES)


def test_incomplete_trailing_quote_line_is_skipped(tmp_path):
    p = tmp_path / "data-dumps" / "research_lab" / "xv_quotes" / "quotes" / "20261110.jsonl"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({"t": T0, "pid": "a", "k_bid": .4, "src": "xv_quotes_v1"}) + "\n" + '{"t": 5, "pid": "b", "k_b')
    assert list(lt.read_quote_file(p, lt.QUOTE_FIELDS, src="xv_quotes_v1")["pid"]) == ["a"]


def _load_runner(name):
    import importlib.util

    s = importlib.util.spec_from_file_location(name, SCRIPTS / "run_live_tests10.py")
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def test_runner_refusals(tmp_path):
    rl = _load_runner("run_live_tests10_a")
    out = tmp_path / "x.json"
    out.write_text("{}")
    assert rl.main(["ops-stats", "--out", str(out), "--root", str(tmp_path)]) == 1  # refuses to overwrite
    assert rl.main(["size-check", "--worlds", "10"]) == 2  # --worlds needs --dev
    assert rl.main(["census-family", "--seal", str(tmp_path / "nope.json")]) == 2  # no seal
    assert rl.main(["analyze"]) == 2  # before the analysis date
    p = tmp_path / "ops.json"
    assert rl.main(["ops-stats", "--out", str(p), "--root", str(tmp_path / "empty")]) == 0 and p.exists()
    assert rl.main(["ops-stats", "--out", str(p), "--root", str(tmp_path / "empty")]) == 1


def test_runner_committed_seal_and_ancestry(tmp_path):
    rl = _load_runner("run_live_tests10_b")
    repo = tmp_path / "repo"
    repo.mkdir()

    def run(*a):
        return subprocess.run(["git", "-C", str(repo), "-c", "user.email=a@b", "-c", "user.name=t", *a], capture_output=True, text=True, check=True).stdout.strip()

    run("init", "-q")
    (repo / "f").write_text("1")
    run("add", "f")
    run("commit", "-qm", "c1")
    h1 = run("rev-parse", "HEAD")
    seal = repo / "seal.json"
    seal.write_text(json.dumps({"e009_analysis_commit": h1, "e010_analysis_commit": h1}))
    assert "not tracked" in rl._committed(seal)[0]
    run("add", "seal.json")
    run("commit", "-qm", "seal")
    err, commit = rl._committed(seal)
    assert err is None and commit == run("rev-parse", "HEAD")
    seal.write_text(json.dumps({"e009_analysis_commit": h1, "e010_analysis_commit": "f" * 40}))
    assert "differs from its committed copy" in rl._committed(seal)[0]
    run("add", "seal.json")
    run("commit", "-qm", "seal2")
    assert "ancestor" in rl._committed(seal)[0]


def test_write_once_and_17g_round_trip(tmp_path):
    p = tmp_path / "data-dumps" / "research_lab" / "live_tests10" / "x" / "a.csv.gz"
    df = pd.DataFrame({"a": [0.1 + 0.2, 1 / 3, 1e-17, 123456789.123456789], "b": ["x", "y", "z", "w"]})
    assert b.write_once_csv(p, df) is True
    assert b.write_once_csv(p, df.assign(a=0.0)) is False  # existing file never touched
    back = pd.read_csv(p, float_precision="round_trip")
    assert (back["a"].to_numpy() == df["a"].to_numpy()).all()  # %.17g: exact round trip
    assert not list(p.parent.glob(".*.tmp"))


def test_cd10_mde_is_max_of_declared_and_design(census_world):
    cd = census_world["cd"]
    for t, v in cd["tests"].items():
        m = v["mde"]
        assert m["mde_c"] == pytest.approx(max(m["declared_c"], m["design_c"]))
        assert v["f_role"] == lt.F_ROLES[t]
        assert v["values"]["DE_gate"] >= 51.0 and v["values"]["OF"] >= 1.0
    f = cd["tests"]["CH224"]["f_mde"]
    assert f["f_mde_c"] == pytest.approx(max(f["declared_c"], f["design_c"]))
    assert "f_mde_ok" in cd["tests"]["CH224"]["gates"] and "f_mde_ok" not in cd["tests"]["CH223"]["gates"]  # only CH224's F-MDE binds


def test_spec_blocks_for_the_analysis_exist():
    spec = lt.load_spec(sha=None)
    assert spec["labels"]["informed_se4_se13"] is False and spec["dropped_tests"] == [] and spec["size_check_result"] is None
    assert set(spec["census_fixed"]["mde_c"]) == set(lt.TESTS) and spec["design_ambiguities"]
    assert spec["economics"]["e009_spec_sha256"] == b.sha256_file(HERE / "model_specs" / "cross_venue_live_v1.json")
    assert spec["vendored"]["cross_venue_live.py"] == b.sha256_file(HERE / "cross_venue_live.py")


def test_history_backfill_pin_and_poller_methods_equal_e009s():
    import inspect
    import textwrap

    assert b.sha256_file(HERE / "history_backfill.py") == "25bef9614222ae7df12a76575cab1a947bdfe0457295172b3d69dd19f08f9d1c"  # pacing / backoff (Limiter, yield_to_live)
    assert "history_backfill.py" in lt.CODE_FILES

    def norm(fn, poller=False):
        src = textwrap.dedent(inspect.getsource(fn))
        src = src.replace("xb.", "").replace("PairState(p, self._seed_hist(pid, now))", "PairState(p)")  # the successor module prefix; no feature history to seed
        tree = ast.parse(src)
        for n in ast.walk(tree):
            if isinstance(n, ast.FunctionDef) and ast.get_docstring(n):
                n.body = n.body[1:]
        return ast.dump(tree)

    for name in ("load_pairs", "active_states", "fetch_kalshi", "fetch_books"):
        assert norm(getattr(xq.XVQuotesPoller, name)) == norm(getattr(e9.Poller, name)), name


def test_zero_overwrite_of_a_refusing_census_and_frozen_not_duplicated(tmp_path):
    df = pd.DataFrame([origin(mk())])
    spec = lt.load_spec(sha=None)
    out = tmp_path / "x" / "live_tests10"
    t = int(df.t.iloc[0])
    assert lt._write_origin(out, t, df, spec, t + 10.0) == "frozen"
    (out / "status" / lt._ymd(t) / (pd.Timestamp(t, unit="s", tz="UTC").strftime("%H%M") + ".csv.gz")).rename(tmp_path / "gone.gz")  # simulate a crash before the status file
    assert lt._write_origin(out, t, df, spec, t + 5000.0) == "exists"  # a late reprocess writes no second frozen copy
    assert not list(out.rglob("*.late.csv.gz"))


def test_partial_pair_file_is_retried_next_run(tmp_path):
    xv = tmp_path / "data-dumps" / "research_lab" / "xv_quotes"
    (xv / "pairs").mkdir(parents=True)
    out = tmp_path / "data-dumps" / "research_lab" / "live_tests10"
    out.mkdir(parents=True)
    f = xv / "pairs" / "pairs_20261109T200000Z.json"
    f.write_text('{"refreshed_utc": "2026-11-09T20:00')
    assert lt.update_seen(xv, out, "r1", 1.0) == set()
    f.write_text(json.dumps({"refreshed_utc": "2026-11-09T20:00:00Z", "pairs": []}))
    assert lt.update_seen(xv, out, "r2", 2.0) == {f.name}
