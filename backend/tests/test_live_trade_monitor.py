"""Live large-trade monitor: dedup, privacy, alert/outcome ordering, immutability, controls."""

from __future__ import annotations

import json
import math

import pytest

from astrolabe.research_lab import live_trade_monitor as ltm

ADDRS = [f"0x{i:040x}" for i in range(1, 40)]
KEY = b"test-key-not-secret"
NOW = 1_800_000_000.0


def trade(i, cid="0xc1", cash=5000.0, addr=None, ts=None, side="BUY", oi=0, price=0.4):
    return {"proxyWallet": addr or ADDRS[i % len(ADDRS)], "side": side, "asset": f"tok{cid}{oi}",
            "conditionId": cid, "size": cash / price, "price": price,
            "timestamp": int((ts or NOW - 30) - i), "outcomeIndex": oi,
            "transactionHash": f"0x{i:064x}", "title": "t", "slug": "s", "name": "NAME",
            "pseudonym": "PSEUDO"}


class FakeLim:
    def __init__(self, feed, flow=None, first=None):
        self.feed, self.flow, self.first = feed, flow or {}, first or {}
        self.requests = self.throttled = 0
        self.urls = []

    def get(self, url, params):
        self.requests += 1
        self.urls.append(url)
        if url.endswith("/trades") and "market" not in params:
            off = params["offset"]
            return 200, self.feed[off: off + params["limit"]]
        if url.endswith("/trades"):
            cid = params["market"]
            return 200, self.flow.get(cid) or [
                {"proxyWallet": ADDRS[(7 * k) % len(ADDRS)], "side": "BUY", "asset": f"tok{cid}0",
                 "size": 100 + k, "price": 0.4, "timestamp": int(NOW - 100 - 60 * k),
                 "outcomeIndex": 0} for k in range(40)]
        if url.endswith("/activity"):
            t = self.first.get(params["user"])
            return 200, [{"timestamp": t}] if t else []
        if url.endswith("/public-profile"):
            return 200, {"createdAt": "2026-10-01T00:00:00Z"}
        if url.endswith("/markets"):
            cid = params["condition_ids"]
            return 200, [{"id": "m" + cid, "bestBid": 0.39, "bestAsk": 0.41, "spread": 0.02,
                          "liquidityNum": 50000, "volume24hr": 1e5, "endDate": "2026-12-01",
                          "oneHourPriceChange": 0.01, "lastTradePrice": 0.4,
                          "clobTokenIds": json.dumps([f"tok{cid}0", f"tok{cid}1"]),
                          "outcomePrices": "[0.4,0.6]", "feeType": "politics",
                          "events": [{"id": "e1"}], "closed": False}]
        return 404, None


@pytest.fixture
def mk(tmp_path):
    def make(feed, **kw):
        lim = FakeLim(feed, **kw)
        cfg = ltm.MonitorConfig(profile=True)
        m = ltm.Monitor(lim, root=tmp_path / "lt", cfg=cfg, key=KEY, clock=lambda: NOW)
        return m, lim
    return make


def force_alerts(m, warmup_days=0.0):
    """Seed a trailing history whose percentile is far below any score."""
    m.cfg.alert_pct, m.cfg.min_history, m.cfg.warmup_days = 0.5, 1, warmup_days
    for rid in m.specs:
        m.score_hist[rid] = [(NOW - 10, -1e9)] * 3


def all_text(root):
    return "".join(p.read_text() for p in root.rglob("*") if p.is_file())


def test_dedup_across_cycles(mk):
    feed = [trade(i) for i in range(5)]
    m, _ = mk(feed)
    s1 = m.run_cycle()
    assert s1["new_trades"] == 5
    assert m.run_cycle()["new_trades"] == 0  # same feed again
    feed.insert(0, trade(50, ts=NOW - 5))
    assert m.run_cycle()["new_trades"] == 1
    rows = list(ltm.read_jsonl(m.root / f"trades-{ltm._day(NOW)}.jsonl"))
    assert len({r["key"] for r in rows}) == len(rows) == 6
    # a restarted process reloads keys from disk and does not re-store the prints
    m2 = ltm.Monitor(FakeLim(feed), root=m.root, cfg=m.cfg, key=KEY, clock=lambda: NOW)
    assert m2.run_cycle()["new_trades"] == 0


def test_min_cash_filter_and_paging(mk):
    feed = [trade(i, cash=5000) for i in range(600)] + [trade(700, cash=10)]
    m, lim = mk(feed)
    m.cfg.max_pages = 2
    assert m.run_cycle()["new_trades"] == 600
    assert sum(u.endswith("/trades") for u in lim.urls) >= 2


def test_no_raw_address_in_any_output(mk):
    feed = [trade(i, cid=f"0xc{i % 3}") for i in range(12)]
    m, lim = mk(feed, first={a: 1_700_000_000 for a in ADDRS})
    force_alerts(m)
    m.run_cycle()
    text = all_text(m.root).lower()
    for a in ADDRS:
        assert a.lower() not in text
        assert a[2:].lower() not in text
    assert "pseudo" not in text and '"name"' not in text
    assert (m.root / "wallets.jsonl").exists()


def test_alerts_written_with_hash_before_outcomes_and_controls(mk):
    feed = [trade(i, cid=f"0xc{i % 4}", cash=2000 + 10 * i) for i in range(20)]
    first = {a: (NOW - 30 * 86400 if k % 2 else NOW - 600) for k, a in enumerate(ADDRS)}
    m, _ = mk(feed, first=first)
    force_alerts(m)
    m.cfg.max_alerts_per_rule = 3
    m.run_cycle()
    lines = list(ltm.read_jsonl(m.root / "alerts.jsonl"))
    alerts = [x for x in lines if x["type"] == "alert"]
    ctrls = [x for x in lines if x["type"] == "control"]
    assert alerts and ctrls
    frozen = m.entries  # unusual-flow set plus the learned surprise rule when frozen
    for a in alerts:
        assert a["rule_sha256"] == frozen[a["rule_id"]]["sha256"]
        assert "outcome" not in json.dumps(a).lower().replace("outcome_index", "")
        assert a["features"] and a["written_utc"]
        assert not (m.root / "outcomes.jsonl").exists()
    for c in ctrls:
        assert c["control_for"] in {a["alert_id"] for a in alerts}
        assert c["features"]["wallet_age_h"] >= ltm.NEW_DAYS * 24
    assert not (m.root / "outcomes.jsonl").exists()


def test_outcome_writer_never_mutates_alerts(mk, tmp_path):
    feed = [trade(i, cid=f"0xc{i % 4}") for i in range(12)]
    m, _ = mk(feed, first={a: NOW - 30 * 86400 for a in ADDRS})
    force_alerts(m)
    m.run_cycle()
    ap = m.root / "alerts.jsonl"
    before = ap.read_bytes()
    assert before

    class Px(FakeLim):
        def get(self, url, params):
            self.requests += 1
            if "prices-history" in url:
                due = (params["startTs"] + params["endTs"]) // 2
                return 200, {"history": [{"t": due + 30, "p": 0.55}]}
            return 200, [{"closed": True, "outcomePrices": "[1,0]"}]

    st = ltm.write_outcomes(Px([]), m.root, now=NOW + 80 * 3600)
    assert st.written > 0
    assert ap.read_bytes() == before
    outs = list(ltm.read_jsonl(m.root / "outcomes.jsonl"))
    ev = [o for o in outs if o.get("status") == "evaluated"]
    assert {o["horizon_h"] for o in ev} == {1, 6, 24, 72}
    assert all(math.isclose(o["move_outcome0"], 0.55 - o["mid_at_receipt"]) for o in ev)
    assert any(o["what"] == "resolution" and o["resolved_outcome0"] == 1.0 for o in outs)
    # idempotent: a second pass writes nothing new
    assert ltm.write_outcomes(Px([]), m.root, now=NOW + 80 * 3600).written == 0
    assert ap.read_bytes() == before


def test_outcomes_not_due_stay_pending(mk):
    m, _ = mk([trade(i, cid=f"0xc{i % 4}") for i in range(8)],
              first={a: NOW - 30 * 86400 for a in ADDRS})
    force_alerts(m)
    m.run_cycle()

    class Never(FakeLim):
        def get(self, url, params):
            raise AssertionError("no request should be needed")

    st = ltm.write_outcomes(Never([]), m.root, now=NOW + 60)
    assert st.written == 0 and st.pending > 0


def row(key, cid, cat, cash, wh, age, ts=0):
    return {"ts": ts, "key": key, "condition_id": cid, "category": cat, "cash": cash,
            "wallet_hash": wh, "wallet_age_h": age}


def test_control_selection():
    a = row("a", "m1", "pol", 5000, "wa", 1.0)
    pool = [a,
            row("same_market", "m1", "pol", 5000, "w1", 900),
            row("other_cat", "m2", "sports", 5000, "w2", 900),
            row("too_big", "m3", "pol", 500000, "w3", 900),
            row("fresh", "m4", "pol", 5000, "w4", 2.0),
            row("unknown_age", "m5", "pol", 5000, "w5", None),
            row("same_wallet", "m6", "pol", 5000, "wa", 900),
            row("ok1", "m7", "pol", 6000, "w7", 900),
            row("ok2", "m8", "pol", 3000, "w8", 400)]
    c, why, rule = ltm.select_control(a, pool)
    assert why == "ok" and c["key"] in {"ok1", "ok2"}
    assert ltm.select_control(a, pool)[0]["key"] == c["key"]  # deterministic
    c2, _, _ = ltm.select_control(a, pool, exclude={c["key"]})
    assert c2["key"] != c["key"]
    none, why, _ = ltm.select_control(a, pool[:7])
    assert none is None and why == "no_control_available"


def test_total_cap_stops(mk):
    m, _ = mk([trade(1)])
    m.cfg.total_cap_bytes = 1
    (m.root / "x.jsonl").write_text("data")
    with pytest.raises(ltm.CapReached):
        m.run_cycle()


def test_day_cap_pauses(mk):
    m, _ = mk([trade(1)])
    m.cfg.day_cap_bytes = 1
    (m.root / f"trades-{ltm._day(NOW)}.jsonl").write_text("xx")
    assert m.run_cycle()["status"] == "day_cap"


def test_httpx_url_logging_silenced():
    import logging

    assert logging.getLogger("httpx").level >= logging.WARNING


def test_control_widens_band_and_logs_rule():
    a = row("a", "m1", "pol", 1000, "wa", 1.0)
    pool = [row("far", "m2", "pol", 8000, "w2", 900), row("old", "m3", "pol", 1000, "w3", 900,
                                                           ts=3 * 86400)]
    c, why, rule = ltm.select_control(a, pool)
    assert c["key"] == "far" and rule["cash_band_factor"] == 10.0  # "old" is outside +-24 h
    assert rule["window_h"] == 24.0 and rule["category"] == "same" and rule["eligible_n"] == 1
    assert ltm.select_control(a, pool, cash_factors=(2.0,))[0] is None


def test_causal_percentile_warmup_and_all_scores_logged(mk):
    feed = [trade(i, cid=f"0xc{i % 4}", cash=2000 + 10 * i) for i in range(20)]
    m, _ = mk(feed, first={a: NOW - 30 * 86400 for a in ADDRS})
    m.cfg.alert_pct, m.cfg.min_history = 0.5, 1
    for rid in m.specs:
        m.score_hist[rid] = [(NOW - 10, -1e9)]
    s = m.run_cycle()  # history younger than warmup_days (7): alerts are warmup, not counted
    assert s["alerts"] == 0 and s["alerts_warmup"] > 0
    al = [x for x in ltm.read_jsonl(m.root / "alerts.jsonl") if x["type"] == "alert"]
    assert al and all(x["warmup"] and x["threshold"] == -1e9 and x["hist_n"] == 1 for x in al)
    sc = list(ltm.read_jsonl(m.root / f"scores-{ltm._day(NOW)}.jsonl"))
    assert len(sc) == 20 and all(set(x["scores"]) == set(m.specs) for x in sc)
    # this cycle's scores entered the history only after thresholds were set
    assert any(len(m.score_hist[rid]) > 1 for rid in m.specs)


def test_no_alert_without_enough_history(mk):
    m, _ = mk([trade(i, cid=f"0xc{i % 4}") for i in range(10)])
    s = m.run_cycle()
    assert s["alerts"] == 0 and s["alerts_warmup"] == 0
    assert not (m.root / "alerts.jsonl").exists() or not list(
        ltm.read_jsonl(m.root / "alerts.jsonl"))


def test_threshold_excludes_current_cycle_and_history_reloads(mk):
    m, _ = mk([trade(i, cid=f"0xc{i % 4}") for i in range(10)],
              first={a: NOW - 30 * 86400 for a in ADDRS})
    m.run_cycle()
    n = {rid: len(v) for rid, v in m.score_hist.items()}
    m2 = ltm.Monitor(FakeLim([]), root=m.root, cfg=m.cfg, key=KEY, clock=lambda: NOW)
    assert {rid: len(v) for rid, v in m2.score_hist.items()} == n
    assert len(m2.recent) == 10  # control pool rebuilt from disk


def test_control_pool_spans_cycles(mk):
    first = {a: NOW - 30 * 86400 for a in ADDRS}
    m, lim = mk([trade(i, cid=f"0xc{i % 4}") for i in range(10)], first=first)
    m.run_cycle()
    lim.feed.insert(0, trade(60, cid="0xc9", ts=NOW - 5))
    force_alerts(m)
    m.run_cycle()
    lines = list(ltm.read_jsonl(m.root / "alerts.jsonl"))
    ctrl = [x for x in lines if x["type"] == "control"]
    assert ctrl and all(c["control_selection"]["pool"] == "received_before_alert" for c in ctrl)
    assert any(c["trade"]["recv_ts"] <= NOW for c in ctrl)


def test_learned_surprise_rule_scored_when_frozen_index_exists(tmp_path):
    """With FROZEN_SURPRISE.json beside FROZEN.json the learned rule is scored from the
    sm_* / price-context features (one prices-history request per market, cached)."""
    import shutil

    from astrolabe.research_lab import detector_eval as de

    spec_dir = tmp_path / "specs"
    spec_dir.mkdir()
    for p in de.SPEC_DIR.glob("*.json"):
        if p.name != ltm.LEARNED_INDEX:
            shutil.copy(p, spec_dir / p.name)
    learned = de.RuleSpec(
        rule_id="sm_test_v1", version="1", theory_ref="surprise_learned",
        terms=({"feature": "sm_abs_imb_1h", "transform": "raw", "center": 0.2, "scale": 0.3,
                "weight": 1.0, "cap": 4.0},
               {"feature": "rv_1d", "transform": "raw", "center": 0.01, "scale": 0.01,
                "weight": -0.5, "cap": 4.0},
               {"feature": "fee_politics", "transform": "raw", "center": 0.0, "scale": 1.0,
                "weight": 0.1, "cap": 4.0}),
        min_terms_present=1, direction_feature="sm_imb_1h")
    de.freeze_rules([learned], spec_dir, index_name=ltm.LEARNED_INDEX, commit="test")

    class PriceLim(FakeLim):
        def get(self, url, params):
            if url.endswith("/prices-history"):
                self.requests += 1
                self.urls.append(url)
                return 200, {"history": [{"t": NOW - 8 * 86400 + 600 * k, "p": 0.4}
                                         for k in range(8 * 144)]}
            return super().get(url, params)

    feed = [trade(i, cid=f"0xc{i % 2}") for i in range(6)]
    lim = PriceLim(feed, first={a: NOW - 30 * 86400 for a in ADDRS})
    m = ltm.Monitor(lim, root=tmp_path / "lt", cfg=ltm.MonitorConfig(profile=True), key=KEY,
                    clock=lambda: NOW, registry=de.RuleRegistry(spec_dir))
    assert "sm_test_v1" in m.specs and m.learned_ids == ["sm_test_v1"]
    m.run_cycle()
    sc = list(ltm.read_jsonl(m.root / f"scores-{ltm._day(NOW)}.jsonl"))
    assert len(sc) == 6 and all("sm_test_v1" in x["scores"] for x in sc)
    assert all(x["scores"]["sm_test_v1"]["alertable"] for x in sc)
    lf = sc[0]["features"]["learned"]
    assert lf["fee_politics"] == 1.0 and math.isfinite(lf["sm_abs_imb_1h"])
    assert math.isfinite(lf["rv_1d"]) and lf["rv_1d"] == 0.0 and lf["sm_covered_24h"] == 1.0
    # one prices-history request per market (cached within the cycle)
    assert sum(u.endswith("/prices-history") for u in lim.urls) == 2
    # without the index: nothing learned, no prices request
    bare = tmp_path / "bare"
    bare.mkdir()
    for p in spec_dir.glob("*.json"):
        if p.name != ltm.LEARNED_INDEX and p.stem != "sm_test_v1":
            shutil.copy(p, bare / p.name)
    m2 = ltm.Monitor(FakeLim(feed), root=tmp_path / "lt2", cfg=ltm.MonitorConfig(), key=KEY,
                     clock=lambda: NOW, registry=de.RuleRegistry(bare))
    assert m2.learned_ids == [] and "learned" not in m2.features_for(
        {"ts": NOW - 30, "size": 1.0}, {"liquidity": 1.0, "token0": "x", "mid": 0.4},
        m2.market_flow("0xc1", "x")[0], 40)
