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


@pytest.mark.parametrize("modname,vendored", [("live_tests10_base.py", b.VENDORED), ("xv_quotes_poller_base.py", xb.VENDORED)])
def test_vendored_provenance_and_drift(modname, vendored):
    text = (HERE / modname).read_text()
    nodes = _nodes(ast.parse(text))
    assert len(vendored) >= 40
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
