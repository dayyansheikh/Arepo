"""Snapshot-path scorer of the ungated surprise-move detector: eligibility, rolling series, stage-1
pre-score, alert/control lines before outcomes, outcome labels."""

from __future__ import annotations

import gzip
import json
import math

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import detector_eval as de
from astrolabe.research_lab import surprise_snapshot as ss

NOW = 1_800_000_000.0
KEY = b"test-key-not-secret"


def capture(tmp_path, t, mids, cap_id="cap1", n=40):
    d = tmp_path / "snapshots" / cap_id
    d.mkdir(parents=True)
    iso = ss.utc_iso(t)
    rows = pd.DataFrame({
        "capture_id": cap_id, "capture_start_utc": iso, "received_utc": iso,
        "market_id": [str(100 + i) for i in range(n)],
        "condition_id": [f"0x{i:064x}" for i in range(n)],
        "event_id": [f"e{i // 2}" for i in range(n)], "closed": False, "active": True,
        "binary": 1, "best_bid": np.array(mids) - 0.01, "best_ask": np.array(mids) + 0.01,
        "spread": 0.02, "last_trade_price": mids, "chg_1h": 0.0, "chg_1d": 0.0, "chg_1w": 0.01,
        "liquidity": 1000.0, "volume24hr": np.arange(n, dtype=float) * 100,
        "end_date": ss.utc_iso(t + 30 * 86400), "updated_at": iso, "dup_count": 0,
        "clob_token_id_0": [f"tok{i}" for i in range(n)], "neg_risk": 0,
        "neg_risk_market_id": np.nan, "neg_risk_other": 0, "event_neg_risk_augmented": 0.0,
        "page_index": 0})
    rows.loc[0, "closed"] = True  # ineligible
    rows.loc[1, "best_ask"] = np.nan  # no two-sided quote
    rows.to_csv(d / "rows.csv.gz", index=False, compression="gzip")
    ext = pd.DataFrame({"market_id": rows["market_id"], "fee_category": "politics",
                        "created_at": ss.utc_iso(t - 10 * 86400)})
    ext.to_csv(d / "rows_ext.csv.gz", index=False, compression="gzip")
    (d / "manifest.json").write_text(json.dumps({
        "capture_id": cap_id, "state": "complete", "started_utc": iso, "finished_utc": iso}))
    return d


def test_eligibility_and_series_proxies(tmp_path):
    mids = np.linspace(0.1, 0.9, 40)
    d = capture(tmp_path, NOW, mids)
    rows, man = ss.load_capture(d)
    el = ss.eligible(rows, ss.SnapshotConfig())
    assert len(el) == 38 and "100" not in set(el["market_id"]) and "101" not in set(
        el["market_id"])
    assert (el["fee_category"] == "politics").all() and np.isfinite(el["created_ts"]).all()
    series = ss.MidSeries(tmp_path / "series.csv.gz")
    rng = np.random.default_rng(0)
    for k in range(90, 0, -1):  # 90 captures on the 2h grid, random walk per market
        el_k = el.copy()
        el_k["t"] = NOW - k * 7200.0
        el_k["mid"] = np.clip(el["mid"] + rng.normal(scale=0.01, size=len(el)), 0.05, 0.95)
        series.add(el_k)
    series.add(el)
    assert len(series.captures()) <= 91 and series.captures().max() == NOW
    rv1 = series.grid_rv(el["market_id"], NOW, 12)
    rv7 = series.grid_rv(el["market_id"], NOW, 84)
    assert np.isfinite(rv1).all() and np.isfinite(rv7).all()
    assert 0.003 < np.median(rv7) < 0.03
    assert np.isfinite(series.mid_at(el["market_id"], NOW - 7200.0)).all()
    assert np.isnan(series.mid_at(el["market_id"], NOW - 7200.0 * 200)).all()
    f = ss.stage1_frame(el, series, NOW)
    assert np.isfinite(f["own_vol"]).all() and np.isfinite(f["proxy_rv_7d"]).all()
    assert (f["sib_n"] >= 0).all() and f["dow"].iloc[0] == float(((NOW // 86400) + 3) % 7)
    spec = de.RuleRegistry(de.SPEC_DIR, ss.LEARNED_INDEX).load(ss.RULE_ID)
    pre = ss.prescore(spec, f)
    assert np.isfinite(pre).all() and len(set(np.round(pre, 6))) > 1
    series.save()
    again = ss.MidSeries(tmp_path / "series.csv.gz")
    assert len(again.df) == len(series.df)


class FakeLim:
    def __init__(self, n_pts=8 * 144):
        self.requests = 0
        self.urls = []
        self.n_pts = n_pts

    def get(self, url, params):
        self.requests += 1
        self.urls.append(url)
        if url.endswith("/prices-history"):
            t0, t1 = int(params["startTs"]), int(params["endTs"])
            ts = np.arange(t0, t1, 600)
            return 200, {"history": [{"t": int(x), "p": 0.4} for x in ts]}
        if url.endswith("/trades"):
            return 200, [{"timestamp": int(NOW - 100 - 60 * k), "side": "BUY", "size": 10.0,
                          "price": 0.4, "outcomeIndex": 0, "proxyWallet": f"0x{k:040x}"}
                         for k in range(30)]
        return 404, None


def test_pass_writes_alerts_and_controls_before_outcomes(tmp_path):
    mids = np.linspace(0.1, 0.9, 40)
    d = capture(tmp_path, NOW, mids)
    lim = FakeLim()
    cfg = ss.SnapshotConfig(candidate_share=0.5, candidate_cap=10, alert_share=0.1, alert_cap=3,
                            k_controls=2)
    sc = ss.Scorer(lim, root=tmp_path / "live", cfg=cfg, key=KEY, clock=lambda: NOW + 60)
    st = sc.run_pass(d)
    assert st["status"] == "ok" and st["n_eligible"] == 38 and st["n_candidates"] == 10
    assert st["n_alerts"] == 3 and st["n_controls"] == 6  # stratum, then price-band fallback
    assert lim.requests == 20  # two requests per candidate, none for controls
    lines = list(ss.read_jsonl(tmp_path / "live" / "alerts.jsonl"))
    alerts = [x for x in lines if x["type"] == "alert"]
    ctrls = [x for x in lines if x["type"] == "control"]
    assert len(alerts) == 3 and len(ctrls) == 6
    for a in alerts:
        assert a["rule_sha256"] == sc.entry["sha256"] and a["evidence_role"] in (
            "prospective_confirmation", "prospective_unregistered")
        assert "outcome" not in json.dumps(a) and math.isfinite(a["score"])
        assert math.isfinite(a["features"]["rv_1d"]) and a["features"]["sm_n_1h"] == 30.0
        assert "proxyWallet" not in json.dumps(a) and "0x0000" not in json.dumps(a["features"])
    cand = {a["market_id"] for a in alerts}
    for c in ctrls:
        assert c["control_for"] in {a["alert_id"] for a in alerts}
        assert c["market_id"] not in cand and c["stratum"]
        assert c["control_match"] in ("stratum", "price_band")
    assert len({c["market_id"] for c in ctrls}) == 6  # never the same control twice
    assert not (tmp_path / "live" / "outcomes.jsonl").exists()
    # idempotent per capture
    assert sc.run_pass(d)["status"] == "already_scored"
    assert len(list(ss.read_jsonl(tmp_path / "live" / "alerts.jsonl"))) == len(lines)
    assert all(abs(a["t"] - (NOW)) < 1 and a["capture_t"] == NOW for a in alerts)  # row receipt
    # outcomes: not due before t + 24h15m -> nothing; due -> one request per line, label fields
    assert ss.write_outcomes(lim, tmp_path / "live", now=NOW + 7 * 3600)["evaluated"] == 0
    assert not (tmp_path / "live" / "outcomes.jsonl").exists()
    r = ss.write_outcomes(lim, tmp_path / "live", now=NOW + 25 * 3600)
    assert r["evaluated"] == 9 and r["requests"] == 9
    outs = list(ss.read_jsonl(tmp_path / "live" / "outcomes.jsonl"))
    assert len(outs) == 9 and all(o["what"] == "label" and o["hit_6h"] is False for o in outs)
    assert all(o["fwd_move_6h"] is not None and o["fwd_move_24h"] is not None for o in outs)
    assert all(o["sharp_any_6h"] is False for o in outs)
    # evaluated lines are not fetched again
    assert ss.write_outcomes(lim, tmp_path / "live", now=NOW + 26 * 3600)["requests"] == 0
    # alerts file untouched by the outcome pass
    assert list(ss.read_jsonl(tmp_path / "live" / "alerts.jsonl")) == lines


def test_label_from_series_detects_a_surprise_departure_after_t():
    ts = np.arange(NOW - 25 * 3600, NOW + 25 * 3600, 600.0)
    p = np.full(len(ts), 0.2)
    j = int(np.searchsorted(ts, NOW + 3 * 3600))
    p[j:] = 0.45
    lab = ss.label_from_series(ts, p, NOW, NOW + 30 * 86400)
    assert lab["hit_6h"] and lab["sharp_any_6h"] and not lab["hit_2h"]
    assert 2.5 < lab["first_dep_lead_h"] <= 3.0 and abs(lab["mid_series_24h"] - 0.45) < 1e-9
    # a departure at t + 5h50 whose arrival (>= 0.15 within 6 h) comes about 3 h later still
    # counts: the fetch window reaches t + 25 h (a 7 h window would have missed it)
    p3 = np.full(len(ts), 0.2)
    k = int(np.searchsorted(ts, NOW + 5.9 * 3600))
    p3[k:k + 20] = 0.26 + 0.10 * np.arange(20) / 20  # leaves the band at once, then creeps
    p3[k + 20:] = 0.36
    lab3 = ss.label_from_series(ts, p3, NOW, NOW + 30 * 86400)
    assert lab3["hit_6h"] and 5.5 < lab3["first_dep_lead_h"] < 6.0
    short = ts <= NOW + 7 * 3600
    assert not ss.label_from_series(ts[short], p3[short], NOW, NOW + 30 * 86400)["hit_6h"]
    p2 = np.full(len(ts), 0.2)
    p2[j - 36 * 6:] = 0.45  # the jump happened a day before t: no departure after t
    lab2 = ss.label_from_series(ts, p2, NOW, NOW + 30 * 86400)
    assert not lab2["hit_6h"]


def test_analyze_handles_empty_and_simple_cases(tmp_path):
    root = tmp_path / "live"
    root.mkdir()
    out = ss.analyze(root)
    assert out["verdict"] == "Unavailable" and out["n_alert_lines"] == 0
    t = ss._epoch(ss.REGISTERED_UTC) + 3600
    lines, outs = [], []
    for i in range(40):
        aid = f"a{i}"
        lines.append({"type": "alert", "alert_id": aid, "market_id": f"m{i}", "event_id": f"e{i}",
                      "t": t + i * 7200 + 500, "capture_t": t + i * 7200, "mid": 0.3,
                      "rule_id": ss.RULE_ID, "evidence_role": "prospective_confirmation"})
        outs.append({"alert_id": aid, "what": "label", "status": "evaluated",
                     "hit_6h": i % 2 == 0, "sharp_any_6h": i % 2 == 0, "fwd_move_6h": 0.2,
                     "fwd_move_24h": 0.2})
        for k in range(3):
            cid = f"c{i}_{k}"
            lines.append({"type": "control", "alert_id": cid, "control_for": aid,
                          "market_id": f"x{i}{k}", "event_id": "", "t": t + i * 7200, "mid": 0.3,
                          "rule_id": ss.RULE_ID, "evidence_role": "prospective_confirmation"})
            outs.append({"alert_id": cid, "what": "label", "status": "evaluated",
                         "hit_6h": False, "sharp_any_6h": False, "fwd_move_6h": 0.0,
                         "fwd_move_24h": 0.0})
    with gzip.open(root / "x.gz", "wt"):
        pass
    ss.append_jsonl(root / "alerts.jsonl", lines)
    ss.append_jsonl(root / "outcomes.jsonl", outs)
    out = ss.analyze(root, n_boot=200)
    assert out["testable"] and out["n_episodes"] == 40 and out["precision_6h"] == 0.5
    assert out["control_base_rate_6h"] == 0.0 and out["verdict"].startswith("Supported")
    assert out["outcome_accounting"]["alert"]["evaluated"] == 40
    # an alert whose capture started before the window is out even if its row time is inside
    early = {"type": "alert", "alert_id": "z", "market_id": "mz", "event_id": "ez",
             "t": ss._epoch(ss.REGISTERED_UTC) + 60, "capture_t": ss._epoch(ss.REGISTERED_UTC) - 60,
             "mid": 0.3, "rule_id": ss.RULE_ID, "evidence_role": "prospective_confirmation"}
    ss.append_jsonl(root / "alerts.jsonl", [early])
    assert ss.analyze(root, n_boot=50)["n_alert_lines"] == 40
    assert out["secondary"]["sharp_any_6h_precision"] == 0.5
    assert out["secondary"]["abs_move_6h_ge_0.15"] == 1.0


@pytest.mark.parametrize("t,role", [(ss._epoch(ss.REGISTERED_UTC) - 1, "prospective_unregistered"),
                                    (ss._epoch(ss.REGISTERED_UTC), "prospective_confirmation"),
                                    (ss._epoch(ss.END_UTC), "prospective_unregistered")])
def test_role_by_registration_window(t, role, tmp_path):
    sc = ss.Scorer(FakeLim(), root=tmp_path / "live", key=KEY)
    assert sc.role(t) == role


def test_archived_extension_sidecar_is_not_read_as_unknown(tmp_path):
    from astrolabe.research_lab import forecast

    d = capture(tmp_path, NOW, np.linspace(0.1, 0.9, 40))
    (d / "ext_manifest.json").write_text("{}")
    (d / "rows_ext.csv.gz").unlink()  # archived and removed by the rotation
    with pytest.raises(forecast.ArchivedDataError):
        ss.load_capture(d)
    (d / "ext_manifest.json").unlink()  # a capture that never had a sidecar still loads as before
    rows, _ = ss.load_capture(d)
    assert (rows["fee_category"] == "unknown").all()
