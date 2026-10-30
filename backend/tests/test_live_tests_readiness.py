"""Readiness checks for the registered live tests E009, E010 and E011 (audit 2026-10-19).

Everything here runs on SYNTHETIC data shaped like the live files: the lines are produced by the
real writers (``cross_venue_live.Poller`` + ``OutcomeWriter``, ``cross_venue_live_e010.E010Writer``,
``surprise_snapshot.Scorer`` + ``write_outcomes``) from generated quotes, never from collected
values. The assertions are accounting identities and registered-rule checks (windows, hygiene,
dedup, gaps, restarts, the 2026-10-14 host move), not effect sizes.
See docs/research_lab/LIVE_TESTS_READINESS_2026-10-19.md.
"""

from __future__ import annotations

import hashlib
import inspect
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

from astrolabe.research_lab import cross_venue_live as cvl
from astrolabe.research_lab import cross_venue_live_e010 as e010
from astrolabe.research_lab import detector_eval as de
from astrolabe.research_lab import economics as econ
from astrolabe.research_lab import surprise_snapshot as ss

H = 3600


def ep(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def _sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# --- 1. frozen artefacts and registered constants ---------------------------------------------


def test_frozen_artefacts_and_constants_match_registration():
    # E009 (EXPERIMENT_LEDGER § E009 "Frozen for the window")
    assert _sha(cvl.SPEC_PATH) == cvl.SPEC_SHA256 == (
        "e63f20cc095ba88346155cabe0d2e4289981017cc48450ccc575bbc7d0d16e2b")
    assert _sha(cvl.VERIFIED_PATH) == (
        "1d6f942a27c9ba1ba56b6514ecb0bad79bd06ce0236084683f722d71932ac54c")
    assert cvl.REGISTERED_UTC == "2026-10-13T00:00:00Z"
    assert (cvl.PRIMARY_H, cvl.HORIZONS_MIN) == (20, (10, 20, 60))
    assert (cvl.MAX_RECV_LAG_S, cvl.OUTCOME_TOL_S, cvl.OUTCOME_GRID_S) == (60, 120, 600)
    sig = inspect.signature(cvl.analyze).parameters
    assert (sig["n_boot"].default, sig["seed"].default) == (4000, 20261012)
    assert sig["role"].default == "prospective_confirmation"
    assert (econ.MIN_TRADES, econ.MIN_CLUSTERS) == (30, 10)
    # E010
    assert _sha(e010.SPEC_PATH) == e010.SPEC_SHA256 == (
        "62b992c6af95ff9a508d8c3130c3ec3ae3333e582bf822d051ea72da46e4961c")
    assert (e010.REGISTERED_UTC, e010.END_UTC) == ("2026-10-13T02:00:00Z", "2026-11-03T00:00:00Z")
    assert (e010.HORIZONS_MIN, e010.ORIGIN_GRID_S) == ((60, 360), 3600)
    sig = inspect.signature(e010.analyze).parameters
    assert (sig["n_boot"].default, sig["seed"].default) == (4000, 20261013)
    # E011
    reg = de.RuleRegistry(de.SPEC_DIR, ss.LEARNED_INDEX)
    assert reg.load(ss.RULE_ID).sha256() == reg.entries()[ss.RULE_ID]["sha256"] == (
        "ee227e7e0b850c6ace940d380aad48f54435a1bc4f487f9250125d2d77c14ef1")
    assert ss.stage1_sha256() == (
        "2f5ef2416346f5f8602e49ee376d7f0ea23abc63a79f0953f9daebee84a679c5")
    assert ss.SnapshotConfig().config_hash() == "7087fec7c4f95feb"
    assert (ss.REGISTERED_UTC, ss.END_UTC) == ("2026-10-13T14:00:00Z", "2026-11-10T00:00:00Z")
    cfg = ss.SnapshotConfig()
    assert (cfg.candidate_cap, cfg.alert_cap, cfg.k_controls) == (400, 60, 3)
    sig = inspect.signature(ss.analyze).parameters
    assert (sig["n_boot"].default, sig["seed"].default) == (4000, 20261013)
    assert sig["start_utc"].default == ss.REGISTERED_UTC and sig["end_utc"].default == ss.END_UTC


# --- 2. E009 + E010 end to end on a synthetic stream with the 10-13/10-14 timeline -------------

PAIRS = [
    {"pid": f"K{i}|P{i}", "k_ticker": f"K{i}", "token0": f"T{i}", "p_event_id": f"E{i // 2}",
     "fee_rate": 0.0 if i % 2 else 0.03}
    for i in range(7)
]
T_FIRST = ep("2026-10-13T21:00:00Z")
T_LAST = ep("2026-10-14T19:10:00Z")
LATE_CYCLE = ep("2026-10-14T13:00:00Z")  # receipts 75 s after the poll (origin late)
NO_BOOK = ("T6", ep("2026-10-14T14:00:00Z"), ep("2026-10-14T14:30:00Z"))  # one-sided Polymarket


def _paths():
    """Synthetic 2-min mid paths on a 0.01 grid: Kalshi random walk, Polymarket follows 10 min
    later with its own noise. Generated from a seed, unrelated to any collected value."""
    rng = np.random.default_rng(20261019)
    n = int((T_LAST - T_FIRST) // 120) + 2
    out = {}
    for i in range(7):
        k = 0.30 + 0.05 * i + np.cumsum(rng.choice([-0.01, 0.0, 0.01], n, p=[0.1, 0.8, 0.1]))
        k = np.clip(np.round(k, 2), 0.10, 0.90)
        p = np.roll(k, 5) + np.round(rng.choice([-0.01, 0.0, 0.01], n, p=[0.15, 0.7, 0.15]), 2)
        p[:5] = k[:5]
        out[f"K{i}"], out[f"T{i}"] = k, np.clip(p, 0.10, 0.90)
    return out


class StreamLim:
    def __init__(self, paths):
        self.paths, self.t, self.requests, self.throttled = paths, T_FIRST, 0, 0

    def _mid(self, key):
        return float(self.paths[key][int((self.t - T_FIRST) // 120)])

    def get(self, url, params):
        self.requests += 1
        if url.endswith("/markets"):
            ms = []
            for tk in params["tickers"].split(","):
                m = self._mid(tk)
                ms.append({"ticker": tk, "yes_bid_dollars": f"{m - 0.01:.2f}",
                           "yes_ask_dollars": f"{m + 0.01:.2f}", "status": "active"})
            return 200, {"markets": ms}
        if url.endswith("/books"):
            out = []
            for d in params:
                tok = d["token_id"]
                m = self._mid(tok)
                one_sided = tok == NO_BOOK[0] and NO_BOOK[1] <= self.t <= NO_BOOK[2]
                out.append({"asset_id": tok,
                            "bids": [{"price": f"{m - 0.01:.2f}", "size": "50"}],
                            "asks": [] if one_sided else [{"price": f"{m + 0.01:.2f}",
                                                           "size": "40"}]})
            return 200, out
        raise AssertionError(url)


def _start(root, lim, clk, now):
    """As run_cross_venue_live.main: E010 writer first (recover), then E009 outcome recovery."""
    p = cvl.Poller(lim, lim, root=root, spec=cvl.load_spec(), clock=clk)
    w = e010.E010Writer(root, spec=e010.load_spec())
    w.recover(now)
    p.extras.append(w)
    p.outcomes.recover(now)
    return p


def _run(p, lim, cur, a, b):
    t = a
    while t <= b:
        lim.t, cur["t"] = t, t
        p.cycle(t)
        t += 120


@pytest.fixture(scope="module")
def stream(tmp_path_factory):
    root = tmp_path_factory.mktemp("cvl")
    (root / "pairs_current.json").write_text(
        json.dumps({"refreshed_utc": "2026-10-13T00:30:00Z", "pairs": PAIRS}))
    lim = StreamLim(_paths())
    cur = {"t": T_FIRST}

    def clk():
        return cur["t"] + (75.0 if cur["t"] == LATE_CYCLE else 1.5)

    a = _start(root, lim, clk, T_FIRST)  # Mac poller
    _run(a, lim, cur, T_FIRST, ep("2026-10-14T00:02:00Z"))
    # Mac asleep 00:02Z-10:44Z: no cycles at all; the same process resumes
    _run(a, lim, cur, ep("2026-10-14T10:44:00Z"), ep("2026-10-14T11:28:00Z"))
    # host move: synced files, new process on the host, the 11:30Z grid point is lost
    b = _start(root, lim, clk, ep("2026-10-14T11:31:00Z"))
    _run(b, lim, cur, ep("2026-10-14T11:32:00Z"), ep("2026-10-14T15:00:00Z"))
    # a supervise restart with outcomes pending at 1h and 6h; the 15:02Z cycle is lost
    c = _start(root, lim, clk, ep("2026-10-14T15:03:00Z"))
    _run(c, lim, cur, ep("2026-10-14T15:04:00Z"), T_LAST)
    return root


def _grid(preds, lo, hi, step):
    out = []
    for r in preds:
        if lo <= r["t"] < hi and r["role"] == "prospective_confirmation" and r["t"] % step == 0:
            if max(r["kr"] - r["t"], r["pr"] - r["t"]) <= cvl.MAX_RECV_LAG_S:
                out.append(r)
    return out


def test_e009_stream_gaps_restarts_and_accounting(stream):
    preds = list(cvl.read_jsonl(stream / "predictions.jsonl"))
    outs = list(cvl.read_jsonl(stream / "outcomes.jsonl"))
    keys = [(o["id"], o["h"]) for o in outs]
    assert len(keys) == len(set(keys)), "a restart duplicated outcome lines"
    assert len({r["id"] for r in preds}) == len(preds)
    ts = sorted({r["t"] for r in preds})
    # nothing during the outage; first prediction after it needs a 60-min lookback (11:44Z)
    assert not [t for t in ts if ep("2026-10-14T00:02:00Z") < t < ep("2026-10-14T11:44:00Z")]
    assert min(t for t in ts if t > ep("2026-10-14T00:02:00Z")) == ep("2026-10-14T11:44:00Z")
    by_id = {r["id"]: r for r in preds}
    # origins whose due fell in the outage are written 'unavailable' when the process resumes
    o0 = [o for o in outs if o["t0"] == ep("2026-10-14T00:00:00Z")]
    assert o0 and {o["status"] for o in o0} == {"unavailable"}
    # the restart C recovered and wrote every pending line exactly once
    lo, hi = ep("2026-10-13T22:00:00Z"), ep("2026-10-14T18:00:00Z")
    now = T_LAST + 1
    res = cvl.analyze(stream, start_utc="2026-10-13T22:00:00Z", end_utc="2026-10-14T18:00:00Z",
                      n_boot=200, now=now)
    assert res["duplicate_outcome_lines"] == 0
    assert res["missing_line"] == {10: 0, 20: 0, 60: 0}
    n_late = sum(1 for r in preds if r["t"] == LATE_CYCLE)
    assert n_late > 0 and res["origin_late"] == n_late
    for h in cvl.HORIZONS_MIN:
        g = _grid(preds, lo, hi, h * 60)
        hz = res["horizons"][str(h)]
        assert hz["status"] == "ok" and hz["n_clusters"] == 4
        # every non-late grid origin is exactly one of: evaluated, unavailable, missing
        assert hz["n_origins"] + res["unavailable"][h] + res["missing_line"][h] == len(g)
        # outcome quotes received > 60 s after their poll (the 13:00Z cycle) are unavailable
        n_late_q = sum(1 for o in outs if o["h"] == h and o["status"] == "evaluated"
                       and o["t_obs"] == LATE_CYCLE and o["id"] in {r["id"] for r in g})
        assert n_late_q > 0 and res["unavailable_late_receipt"][h] == n_late_q
    # one-sided book -> no prediction for that pair while it lasts
    assert not [r for r in preds if r["pid"] == "K6|P6" and NO_BOOK[1] <= r["t"] <= NO_BOOK[2]]
    # determinism (fixed seed) and dedup keeps the first line
    again = cvl.analyze(stream, start_utc="2026-10-13T22:00:00Z", end_utc="2026-10-14T18:00:00Z",
                        n_boot=200, now=now)
    assert json.dumps(again, default=float) == json.dumps(res, default=float)
    first = next(o for o in outs if o["h"] == 20 and o["status"] == "evaluated"
                 and by_id[o["id"]]["t"] % 1200 == 0 and lo <= o["t0"] < hi)
    dup = stream / "dup"
    dup.mkdir()
    for f in ("predictions.jsonl", "outcomes.jsonl"):
        (dup / f).write_bytes((stream / f).read_bytes())
    cvl.append_jsonl(dup / "outcomes.jsonl", [{**first, "dp": first["dp"] + 0.5}])
    res2 = cvl.analyze(dup, start_utc="2026-10-13T22:00:00Z", end_utc="2026-10-14T18:00:00Z",
                       n_boot=200, now=now)
    assert res2["duplicate_outcome_lines"] == 1
    assert res2["horizons"]["20"]["rel_mse_gain"] == res["horizons"]["20"]["rel_mse_gain"]
    # window edges: START inclusive, END exclusive (origin t)
    t1 = min(r["t"] for r in _grid(preds, lo, hi, 1200))
    a1 = cvl.analyze(stream, start_utc=cvl.utc_iso(t1), end_utc="2026-10-14T18:00:00Z",
                     n_boot=20, now=now)
    a2 = cvl.analyze(stream, start_utc=cvl.utc_iso(t1 + 1), end_utc="2026-10-14T18:00:00Z",
                     n_boot=20, now=now)
    n_t1 = sum(1 for r in _grid(preds, lo, hi, 1200) if r["t"] == t1)
    assert (a1["horizons"]["20"]["n_origins"] + a1["unavailable"][20]
            - a2["horizons"]["20"]["n_origins"] - a2["unavailable"][20]) == n_t1
    # the role filter: pilot-role lines never enter the confirmation analysis
    un = cvl.analyze(stream, start_utc="2026-10-13T22:00:00Z", end_utc="2026-10-14T18:00:00Z",
                     n_boot=20, now=now, role="prospective_unregistered")
    assert un["horizons"]["20"]["status"] == "insufficient"


def test_e010_stream_gaps_restarts_and_accounting(stream):
    preds = list(cvl.read_jsonl(stream / e010.PRED_FILE))
    outs = list(cvl.read_jsonl(stream / e010.OUT_FILE))
    keys = [(o["id"], o["h"]) for o in outs]
    assert len(keys) == len(set(keys))
    assert {r["t"] % 3600 for r in preds} == {0}
    hours = sorted({r["t"] for r in preds if r["t"] < ep("2026-10-14T13:00:00Z")})
    assert hours == [ep(s) for s in ("2026-10-13T22:00:00Z", "2026-10-13T23:00:00Z",
                                     "2026-10-14T00:00:00Z", "2026-10-14T12:00:00Z")]
    # 6h outcomes due inside the outage are unavailable; the 12:00Z origin's 6h line is written
    # by the process started after the 15:00Z restart, at its exact due quote
    for s in ("2026-10-13T22:00:00Z", "2026-10-13T23:00:00Z", "2026-10-14T00:00:00Z"):
        o = next(o for o in outs if o["t0"] == ep(s) and o["h"] == 360)
        assert o["status"] == "unavailable"
    o12 = [o for o in outs if o["t0"] == ep("2026-10-14T12:00:00Z") and o["h"] == 360]
    assert o12 and all(o["status"] == "evaluated" and o["t_obs"] == ep("2026-10-14T18:00:00Z")
                       for o in o12)
    now = T_LAST + 1
    res = e010.analyze(stream, start_utc="2026-10-13T22:00:00Z",
                       end_utc="2026-10-14T13:00:00Z", n_boot=200, now=now)
    lo, hi = ep("2026-10-13T22:00:00Z"), ep("2026-10-14T13:00:00Z")
    g = _grid(preds, lo, hi, 3600)
    assert res["duplicate_outcome_lines"] == 0 and res["missing_line"] == {60: 0, 360: 0}
    for h in e010.HORIZONS_MIN:
        hz = res["horizons"][str(h)]
        n_ok = hz.get("n_origins", 0)
        assert n_ok + res["unavailable"][h] + res["missing_line"][h] == len(g)
    # Holm always over both registered primaries, adjusted p >= raw p
    assert set(res["holm_m1"]) == {"60", "360"}
    for h in ("60", "360"):
        hz = res["horizons"][h]
        if hz["status"] == "ok":
            assert res["holm_m1"][h] >= hz["p_one_sided_m1"]
        else:
            assert res["holm_m1"][h] == 1.0
    # the late 13:00Z cycle: excluded as late, not silently dropped
    late = e010.analyze(stream, start_utc="2026-10-13T22:00:00Z",
                        end_utc="2026-10-14T14:00:00Z", n_boot=20, now=now)
    assert late["origin_late"] == sum(1 for r in preds if r["t"] == LATE_CYCLE) > 0


# --- 3. E011 end to end through the Scorer and outcome writer -----------------------------------

N_MKT = 40


def _capture(root, t, cap_id):
    import pandas as pd

    d = root / "snapshots" / cap_id
    d.mkdir(parents=True)
    iso = ss.utc_iso(t)
    mids = np.linspace(0.1, 0.9, N_MKT)
    rows = pd.DataFrame({
        "capture_id": cap_id, "capture_start_utc": iso, "received_utc": ss.utc_iso(t + 300),
        "market_id": [str(100 + i) for i in range(N_MKT)],
        "condition_id": [f"0x{i:064x}" for i in range(N_MKT)],
        "event_id": [f"e{i // 2}" for i in range(N_MKT)], "closed": False, "active": True,
        "binary": 1, "best_bid": mids - 0.01, "best_ask": mids + 0.01, "spread": 0.02,
        "last_trade_price": mids, "chg_1h": 0.0, "chg_1d": 0.0, "chg_1w": 0.01,
        "liquidity": 1000.0, "volume24hr": np.arange(N_MKT, dtype=float) * 100,
        "end_date": ss.utc_iso(t + 30 * 86400), "updated_at": iso, "dup_count": 0,
        "clob_token_id_0": [f"tok{i}" for i in range(N_MKT)], "neg_risk": 0,
        "neg_risk_market_id": np.nan, "neg_risk_other": 0, "event_neg_risk_augmented": 0.0,
        "page_index": 0})
    rows.to_csv(d / "rows.csv.gz", index=False, compression="gzip")
    pd.DataFrame({"market_id": rows["market_id"], "fee_category": "politics",
                  "created_at": ss.utc_iso(t - 10 * 86400)}).to_csv(
        d / "rows_ext.csv.gz", index=False, compression="gzip")
    (d / "manifest.json").write_text(json.dumps({
        "capture_id": cap_id, "state": "complete", "started_utc": iso, "finished_utc": iso}))
    return d


class SnapLim:
    """Stage-2 and outcome endpoints. Outcome requests (a 50 h window) depend on the token: every
    3rd jumps by 0.25 three hours after t (a departure), every 7th returns 200 with no history
    (unavailable 12 h after due), every 11th returns 503 (stays pending)."""

    def __init__(self):
        self.requests, self.t = 0, 0.0

    def get(self, url, params):
        self.requests += 1
        if url.endswith("/trades"):
            return 200, [{"timestamp": int(self.t - 100 - 60 * k), "side": "BUY", "size": 10.0,
                          "price": 0.4, "outcomeIndex": 0, "proxyWallet": f"0x{k:040x}"}
                         for k in range(30)]
        if url.endswith("/prices-history"):
            a, b = int(params["startTs"]), int(params["endTs"])
            i = int(str(params["market"]).removeprefix("tok"))
            if b - a == 50 * H:
                if i % 11 == 0:
                    return 503, None
                if i % 7 == 0:
                    return 200, {"history": []}
            t_line = a + 25 * H
            ts = np.arange(a, b, 600)
            p = np.where((i % 3 == 0) & (ts >= t_line + 3 * H) & (b - a == 50 * H), 0.65, 0.40)
            return 200, {"history": [{"t": int(x), "p": float(y)} for x, y in zip(ts, p,
                                                                                  strict=True)]}
        return 404, None


def test_e011_passes_outcomes_and_accounting(tmp_path):
    live = tmp_path / "surprise_live"
    lim = SnapLim()
    cur = {"t": 0.0}
    cfg = ss.SnapshotConfig(candidate_share=0.5, candidate_cap=10, alert_share=0.1, alert_cap=3,
                            k_controls=2)
    sc = ss.Scorer(lim, root=live, cfg=cfg, key=b"synthetic-key", clock=lambda: cur["t"])
    caps = {}
    # 12:31Z is before REGISTERED_UTC (unregistered); 18:31Z is a missed pass (host gap)
    for s in ("2026-10-13T12:31:00Z", "2026-10-13T14:31:00Z", "2026-10-13T16:31:00Z",
              "2026-10-13T20:31:00Z", "2026-10-13T22:31:00Z"):
        t = ep(s)
        cur["t"], lim.t = t + 600, t + 300
        caps[s] = _capture(tmp_path, t, s.replace(":", ""))
        st = sc.run_pass(caps[s])
        assert st["status"] == "ok" and st["n_alerts"] == 3
    n_lines = len(list(ss.read_jsonl(live / "alerts.jsonl")))
    assert sc.run_pass(caps["2026-10-13T16:31:00Z"])["status"] == "already_scored"
    assert len(list(ss.read_jsonl(live / "alerts.jsonl"))) == n_lines
    lines = list(ss.read_jsonl(live / "alerts.jsonl"))
    alerts = [x for x in lines if x["type"] == "alert"]
    win = [a for a in alerts if a["evidence_role"] == "prospective_confirmation"]
    assert len(alerts) == 15 and len(win) == 12
    assert all(a["capture_t"] >= ep(ss.REGISTERED_UTC) for a in win)
    # outcome passes: before due nothing; later passes never duplicate a line
    last_t = max(x["t"] for x in lines if x["type"] in ("alert", "control"))
    assert ss.write_outcomes(lim, live, now=last_t + 3600)["evaluated"] == 0
    ss.write_outcomes(lim, live, now=last_t + ss.OUTCOME_DUE_S + 60)
    ss.write_outcomes(lim, live, now=last_t + ss.OUTCOME_DUE_S + 13 * H)
    ss.write_outcomes(lim, live, now=last_t + ss.OUTCOME_DUE_S + 14 * H)
    outs = list(ss.read_jsonl(live / "outcomes.jsonl"))
    assert len({o["alert_id"] for o in outs}) == len(outs)
    status = {o["alert_id"]: o["status"] for o in outs}

    def tok(x):
        return int(x["token0"].removeprefix("tok"))

    for x in lines:
        if x["type"] not in ("alert", "control"):
            continue
        want = ("pending" if tok(x) % 11 == 0 else "unavailable" if tok(x) % 7 == 0
                else "evaluated")
        assert status.get(x["alert_id"], "pending") == want
    res = ss.analyze(live, n_boot=200)
    assert res["n_alert_lines"] == 12
    acc = res["outcome_accounting"]
    assert sum(acc["alert"].values()) == 12
    ctrl_win = [c for c in lines if c["type"] == "control"
                and c["control_for"] in {a["alert_id"] for a in win}]
    assert sum(acc["control"].values()) == len(ctrl_win)
    assert acc["alert"]["pending"] == sum(1 for a in win if tok(a) % 11 == 0)
    # episodes: alert lines of one market less than 24 h apart collapse to the first
    assert res["n_episodes"] == len({a["market_id"] for a in win})
    assert res["n_episodes_analysed"] + sum(res["dropped_episodes"].values()) == res["n_episodes"]
    assert res["verdict"] == "Unavailable"  # < 30 episodes: the registered minimum applies


def _line(aid, m, ev, t, cap_t=None, role="prospective_confirmation", **kw):
    return {"type": "alert", "alert_id": aid, "market_id": m, "event_id": ev, "t": t,
            "capture_t": t if cap_t is None else cap_t, "mid": 0.3, "rule_id": ss.RULE_ID,
            "evidence_role": role, "fee_category": "politics", **kw}


def _lab(aid, hit, **kw):
    return {"alert_id": aid, "what": "label", "status": "evaluated", "hit_6h": hit,
            "sharp_any_6h": hit, "fwd_move_6h": 0.0, "fwd_move_24h": 0.0, **kw}


def _write(root, alerts, n_ctrl=3, a_hit=None, c_hit=None):
    lines, outs = [], []
    for k, a in enumerate(alerts):
        lines.append(a)
        outs.append(_lab(a["alert_id"], bool(a_hit(k)) if a_hit else False))
        for j in range(n_ctrl):
            cid = f"{a['alert_id']}_c{j}"
            lines.append({"type": "control", "alert_id": cid, "control_for": a["alert_id"],
                          "market_id": f"x{k}_{j}", "event_id": f"xe{k}", "t": a["t"],
                          "mid": 0.3, "rule_id": ss.RULE_ID, "evidence_role": a["evidence_role"]})
            outs.append(_lab(cid, bool(c_hit(k)) if c_hit else False))
    ss.append_jsonl(root / "alerts.jsonl", lines)
    ss.append_jsonl(root / "outcomes.jsonl", outs)


def test_e011_episode_chaining_window_edges_and_verdicts(tmp_path):
    t0 = ep(ss.REGISTERED_UTC) + 1800
    # chaining: lines at 0, 20 h, 40 h collapse (each < 24 h after the previous line); 65 h is new
    r1 = tmp_path / "chain"
    r1.mkdir()
    _write(r1, [_line(f"a{k}", "m1", "e1", t0 + dt * H) for k, dt in enumerate((0, 20, 40, 65))])
    out = ss.analyze(r1, n_boot=50)
    assert out["n_alert_lines"] == 4 and out["n_episodes"] == 2
    # window membership by capture start: END itself is out, END - 1 s is in
    r2 = tmp_path / "edge"
    r2.mkdir()
    end = ep(ss.END_UTC)
    _write(r2, [_line("in", "m1", "e1", end + 400, cap_t=end - 1),
                _line("out", "m2", "e2", end + 400, cap_t=end),
                _line("early", "m3", "e3", t0, cap_t=ep(ss.REGISTERED_UTC) - 1),
                _line("unreg", "m4", "e4", t0, role="prospective_unregistered")])
    assert ss.analyze(r2, n_boot=50)["n_alert_lines"] == 1
    # Contradicted: alerts never hit, controls always do (CI entirely below 0)
    r3 = tmp_path / "contra"
    r3.mkdir()
    _write(r3, [_line(f"a{k}", f"m{k}", f"e{k}", t0 + k * 600) for k in range(40)],
           a_hit=lambda k: False, c_hit=lambda k: True)
    assert ss.analyze(r3, n_boot=200)["verdict"] == "Contradicted"
    # Unavailable with >= 30 episodes but < 10 clusters
    r4 = tmp_path / "fewcl"
    r4.mkdir()
    _write(r4, [_line(f"a{k}", f"m{k}", f"e{k % 5}", t0 + k * 600) for k in range(40)],
           a_hit=lambda k: k % 2 == 0)
    o4 = ss.analyze(r4, n_boot=200)
    assert o4["n_clusters"] == 5 and o4["verdict"] == "Unavailable"
    # Inconclusive: no difference
    r5 = tmp_path / "flat"
    r5.mkdir()
    _write(r5, [_line(f"a{k}", f"m{k}", f"e{k}", t0 + k * 600) for k in range(40)])
    assert ss.analyze(r5, n_boot=200)["verdict"] == "Inconclusive"


def test_e011_missing_event_id_falls_back_to_market_id(tmp_path):
    """Registered cluster = Gamma event id, market id when absent. Alert lines store
    str(event_id), so a capture row without one arrives as 'nan'; those markets must not be
    pooled into one 'nan' cluster (fix in surprise_snapshot._cluster_id, readiness audit)."""
    t0 = ep(ss.REGISTERED_UTC) + 1800
    _write(tmp_path, [_line(f"a{k}", f"m{k}", ("nan", "None", "", None)[k % 4], t0 + k * 600)
                      for k in range(40)], a_hit=lambda k: k % 2 == 0)
    out = ss.analyze(tmp_path, n_boot=100)
    assert out["n_clusters"] == 40 and out["testable"]
    assert ss._cluster_id({"event_id": "123", "market_id": "9"}) == "123"
    assert ss._cluster_id({"event_id": "nan", "market_id": "9"}) == "9"


def test_e011_outcome_lines_are_one_per_line_and_pending_is_never_imputed(tmp_path):
    t0 = ep(ss.REGISTERED_UTC) + 1800
    alerts = [_line(f"a{k}", f"m{k}", f"e{k}", t0 + k * 600) for k in range(35)]
    _write(tmp_path, alerts)
    # drop the outcome lines of 5 alerts: they stay pending and their episodes are dropped
    outs = [o for o in ss.read_jsonl(tmp_path / "outcomes.jsonl")
            if o["alert_id"] not in {f"a{k}" for k in range(5)}]
    (tmp_path / "outcomes.jsonl").unlink()
    ss.append_jsonl(tmp_path / "outcomes.jsonl", outs)
    out = ss.analyze(tmp_path, n_boot=100)
    assert out["outcome_accounting"]["alert"]["pending"] == 5
    assert out["dropped_episodes"]["no_alert_label"] == 5 and out["n_episodes_analysed"] == 30
